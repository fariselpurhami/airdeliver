"""S08 mounted products route input and SQL pagination boundaries."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from app.api.v1.endpoints import products
from app.db.session import get_async_session


class ProductResult:
    def scalars(self):
        return self
    def all(self):
        return []


def harness():
    db = SimpleNamespace(execute=AsyncMock(return_value=ProductResult()))
    app = FastAPI()
    app.include_router(products.router, prefix="/products")
    async def session():
        yield db
    app.dependency_overrides[get_async_session] = session
    return app, db


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [
    "skip=-1", "skip=100001", "skip=99999999999999999999999999999",
    "limit=0", "limit=-1", "limit=101", "limit=99999999999999999999999999",
    "page=0", "page=-1", "page=100002", "page=100001&limit=100",
    "skip=no", "limit=no", "page=no",
])
async def test_invalid_pagination_is_rejected_before_sql(query):
    app, db = harness()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products/?" + query)
    assert response.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("query,offset,limit", [
    ("", 0, 100),
    ("skip=7&limit=3", 7, 3),
    ("skip=7&page=1&limit=3", 0, 3),
    ("skip=7&page=2&limit=3", 3, 3),
    ("skip=100000&limit=1", 100000, 1),
    ("page=100001&limit=1", 100000, 1),
])
async def test_valid_pagination_has_bounded_consistent_sql_offset(query, offset, limit):
    app, db = harness()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products/?" + query)
    assert response.status_code == 200
    assert response.json() == []
    statement = db.execute.await_args.args[0]
    parameters = statement.compile(dialect=postgresql.dialect()).params
    assert parameters["param_1"] == limit
    assert parameters["param_2"] == offset


@pytest.mark.asyncio
async def test_no_slash_route_has_identical_validation():
    app, db = harness()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?limit=-1")
    assert response.status_code == 422
    db.execute.assert_not_awaited()
