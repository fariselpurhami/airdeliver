"""CAP-01 actual PostgreSQL execution, not SQL-string matching."""
import os
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy import delete,text,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_commerce_engine import AICommerceEngine,SearchFilter,ValidationError

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest_asyncio.fixture
async def catalog():
    native=create_async_engine(os.environ['TEST_POSTGRES_DSN'])
    sessions=async_sessionmaker(native,expire_on_commit=False)
    category='filter-'+uuid4().hex
    async with sessions() as db:
        assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
        rows=[Product(sku=uuid4().hex,name='Unique filter headphone '+str(i),description='',category=category,
                      price=price,inventory=4,is_active=active,rating=5-i*.1)
              for i,(price,active) in enumerate([(10,True),(20,True),(30,True),(20,False),(20,True)])]
        rows[-1].category='other-'+category
        db.add_all(rows);await db.commit()
    try:yield sessions,rows,category
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_([r.id for r in rows])));await db.commit()
        await native.dispose()


def engine():return AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object())


@pytest.mark.asyncio
async def test_filter_roundtrip_executes_current_sql_prices_category_activity_and_exclusions(catalog):
    sessions,rows,category=catalog
    raw={'price_min':'10','price_max':'20','category':category,'excluded_ids':[str(rows[0].id),rows[0].id]}
    filters=SearchFilter.from_mapping(SearchFilter.from_mapping(raw).to_cache_dict())
    async with sessions() as db:
        result=await engine()._fallback_sql_search(db,'Unique filter headphone',20,filters)
        assert [r.id for r in result]==[rows[1].id]
    async with sessions() as writer:
        await writer.execute(update(Product).where(Product.id==rows[1].id).values(price=25));await writer.commit()
    async with sessions() as db:
        assert await engine()._fallback_sql_search(db,'Unique filter headphone',20,filters)==[]
    # Data remains present and unchanged by the read path.
    async with sessions() as db:
        assert (await db.get(Product,rows[1].id)).price==25


@pytest.mark.asyncio
async def test_search_text_normalization_and_injection_like_category_cannot_widen_sql(catalog):
    sessions,rows,category=catalog
    async with sessions() as db:
        filters=SearchFilter.from_mapping({'category':category+"' OR 1=1 --"})
        assert await engine()._fallback_sql_search(db,'Unique filter headphone',20,filters)==[]
        assert await engine()._fallback_sql_search(db,'!!!',20,SearchFilter())==[]
        result=await engine()._fallback_sql_search(db,'Unique\nfilter   headphone',1,SearchFilter(category=category))
        assert [r.id for r in result]==[rows[0].id]


@pytest.mark.asyncio
async def test_invalid_filter_rejected_before_actual_database_query(catalog):
    sessions,rows,category=catalog
    for raw in [{'price_max':float('nan')},{'price_min':30,'price_max':10},{'excluded_ids':[True]}]:
        with pytest.raises(ValidationError):SearchFilter.from_mapping(raw)
    async with sessions() as db:
        result=await engine()._fallback_sql_search(db,'Unique filter headphone',20,SearchFilter(category=category))
        assert {r.id for r in result}=={r.id for r in rows[:3]}
