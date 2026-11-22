"""Regression tests for search constraints at external/SQL fallback boundaries."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from app.services.ai_commerce_engine import AICommerceEngine, EngineLimits, SearchFilter, ValidationError
from app.models.product import Product


def test_excluded_ids_survive_mapping():
    assert SearchFilter.from_mapping({"excluded_ids": [3, "7", 3]}).excluded_ids == [3, 7]


@pytest.mark.parametrize("value", [[True], [0], [-3], [1.5], ["1 or id > 0"], "1,2"])
def test_excluded_ids_reject_invalid_values(value):
    with pytest.raises(ValidationError):
        SearchFilter.from_mapping({"excluded_ids": value})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_price_rejected(value):
    with pytest.raises(ValidationError):
        SearchFilter.from_mapping({"price_max": value})


@pytest.mark.asyncio
async def test_sql_fallback_respects_all_filters():
    engine = object.__new__(AICommerceEngine)
    engine.limits = EngineLimits()
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    filters = SearchFilter(price_min=10, price_max=25, category="audio", excluded_ids=[7])
    await engine._fallback_sql_search(db, "headphones", 5, filters)
    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "products.price >= 10" in sql
    assert "products.price <= 25" in sql
    assert "products.category = 'audio'" in sql
    assert "products.id NOT IN (7)" in sql
    assert "products.is_active IS true" in sql


@pytest.mark.asyncio
async def test_bundle_never_uses_one_db_session_concurrently():
    engine = object.__new__(AICommerceEngine)
    engine.limits = EngineLimits()
    engine.cache_client = None
    engine.bootstrap = AsyncMock()
    active = 0
    maximum = 0
    async def search(*args, **kwargs):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.005)
        active -= 1
        return []
    engine.perform_hybrid_search_pure = search
    anchor = Product(id=1, sku="anchor", name="phone", description="", price=100)
    engine._fetch_products_from_db_by_ids = AsyncMock(return_value=[anchor])
    await engine.generate_perfect_bundle(AsyncMock(), anchor)
    assert maximum == 1
