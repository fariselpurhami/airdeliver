"""Recommendation truth against migrated PostgreSQL, not index/cache snapshots.

Only retrieval/cache transport is controlled. Products are committed, changed and
read through independent real PostgreSQL sessions. No model/provider traffic.
"""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, text, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models.product import Product
from app.services.ai_commerce_engine import AICommerceEngine, EngineLimits

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='requires migrated disposable PostgreSQL')


@pytest_asyncio.fixture
async def catalog():
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN'])
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with sessions() as db:
        assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
        rows=[Product(sku=uuid4().hex,name=name,description='',category='Electronics',price=price,inventory=10)
              for name,price in [('Anchor Phone',100),('Phone case',20),('Phone cable',15),('Phone stand',30)]]
        for row in rows[1:]:
            row.attributes={'complement_for_skus': __import__('json').dumps([rows[0].sku])}
        db.add_all(rows);await db.commit()
    yield sessions,rows
    async with sessions() as db:
        await db.execute(delete(Product).where(Product.id.in_([p.id for p in rows])))
        await db.commit()
    await engine.dispose()


def make_engine(cache=None, milvus=None):
    engine=AICommerceEngine(opensearch_client=object(),milvus_client=milvus or object(),embedding_model=object(),cache_client=cache)
    engine.bootstrap=AsyncMock()
    engine.perform_hybrid_search_pure=AsyncMock(return_value=[])
    return engine


@pytest.mark.asyncio
async def test_bundle_cache_uses_current_rows_not_old_product_snapshots(catalog):
    sessions,(anchor,kept,inactive,deleted)=catalog
    snapshots=[p.model_dump(mode='json') for p in [kept,inactive,deleted]]
    cache=SimpleNamespace(get_json=AsyncMock(return_value=snapshots),set_json=AsyncMock())
    engine=make_engine(cache)
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==kept.id).values(price=25,name='Current phone case'))
        await db.execute(update(Product).where(Product.id==inactive.id).values(is_active=False))
        await db.execute(delete(Product).where(Product.id==deleted.id));await db.commit()
    async with sessions() as db:
        result=await engine.generate_perfect_bundle(db,anchor)
    assert [(p.id,p.name,str(p.price)) for p in result]==[(kept.id,'Current phone case','25.00')]


@pytest.mark.asyncio
async def test_bundle_cache_rechecks_live_anchor_budget_and_excludes_anchor(catalog):
    sessions,(anchor,*others)=catalog
    cache=SimpleNamespace(get_json=AsyncMock(return_value=[p.model_dump(mode='json') for p in [anchor,*others]]),set_json=AsyncMock())
    engine=make_engine(cache)
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==anchor.id).values(price=60));await db.commit()
    # Caller may still hold old anchor price100; current price60 gives cap36.
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==others[0].id).values(price=50));await db.commit()
    async with sessions() as db:
        result=await engine.generate_perfect_bundle(db,anchor)
    assert {p.id for p in result}=={others[1].id,others[2].id}


@pytest.mark.asyncio
async def test_stale_vector_alternatives_cannot_bypass_current_activity_price_category(catalog):
    sessions,(anchor,wrong_price,inactive,wrong_category)=catalog
    # Index says all are same-category/70..130. PostgreSQL says otherwise.
    class Index:
        def query(self,*a,**k):return [{'vector':[1.0]}]
        def search(self,*a,**k):return [[{'entity':{'id':p.id}} for p in [wrong_price,inactive,wrong_category]]]
    engine=make_engine(milvus=Index())
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==inactive.id).values(price=100,is_active=False))
        await db.execute(update(Product).where(Product.id==wrong_category.id).values(price=100,category='Different'))
        await db.commit()
    async with sessions() as db:
        result=await engine.find_genius_alternatives(db,anchor.id)
    assert result==[]


@pytest.mark.asyncio
async def test_sql_alternative_fallback_excludes_inactive_rows(catalog):
    sessions,(anchor,*others)=catalog
    class EmptyIndex:
        def query(self,*a,**k):return []
    engine=make_engine(milvus=EmptyIndex())
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id.in_([p.id for p in others])).values(price=100,is_active=False))
        await db.commit()
    async with sessions() as db:
        result=await engine.find_genius_alternatives(db,anchor.id)
    assert result==[]


@pytest.mark.asyncio
async def test_bundle_refreshes_rows_already_in_same_session_identity_map(catalog):
    sessions,(anchor,kept,*_)=catalog
    cache=SimpleNamespace(get_json=AsyncMock(return_value=[kept.model_dump(mode='json')]),set_json=AsyncMock())
    engine=make_engine(cache)
    async with sessions() as viewer:
        old=await viewer.get(Product,kept.id)
        assert str(old.price)=='20.00'
        async with sessions() as writer:
            await writer.execute(update(Product).where(Product.id==kept.id).values(price=26))
            await writer.commit()
        result=await engine.generate_perfect_bundle(viewer,anchor)
        assert str(result[0].price)=='26.00'


@pytest.mark.asyncio
async def test_new_bundle_cache_contains_ids_and_replays_current_price(catalog):
    sessions,(anchor,kept,*_)=catalog
    cache=SimpleNamespace(get_json=AsyncMock(return_value=None),set_json=AsyncMock())
    engine=make_engine(cache)
    engine.perform_hybrid_search_pure=AsyncMock(return_value=[kept])
    async with sessions() as db:
        result=await engine.generate_perfect_bundle(db,anchor)
        assert [p.id for p in result]==[kept.id]
    stored=cache.set_json.await_args.args[1]
    assert stored==[kept.id]
    cache.get_json.return_value=stored
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==kept.id).values(price=27));await db.commit()
    async with sessions() as db:
        result=await engine.generate_perfect_bundle(db,anchor)
        assert str(result[0].price)=='27.00'


@pytest.mark.asyncio
async def test_malformed_cache_does_not_disable_existing_bundle_retrieval(catalog):
    sessions,(anchor,kept,*_)=catalog
    cache=SimpleNamespace(get_json=AsyncMock(return_value=[True,{'id':'invalid'},-1,2**65]),set_json=AsyncMock())
    engine=make_engine(cache)
    engine.perform_hybrid_search_pure=AsyncMock(return_value=[kept])
    async with sessions() as db:
        result=await engine.generate_perfect_bundle(db,anchor)
        assert [p.id for p in result]==[kept.id]


@pytest.mark.asyncio
@pytest.mark.parametrize('change,quantity,existing', [
    ({'is_active':False},1,0),
    ({'inventory':0},1,0),
    ({'inventory':2},3,0),
    ({'inventory':3},2,2),
    ({'inventory':500},50,60),
])
async def test_cart_add_rejects_unavailable_or_excess_total_without_mutation(catalog,change,quantity,existing):
    from app.services.ai_cart_service import AICartService
    from tests.test_ai_cart_service import FakeCache
    sessions,(anchor,*_)=catalog
    original={'items':[{'product_id':anchor.id,'name':anchor.name,'price':'100','quantity':existing}]} if existing else None
    cache=FakeCache(original)
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==anchor.id).values(**change));await db.commit()
    async with sessions() as db:
        await AICartService(db,cache,object()).handle_add_to_cart({'user_id':1,'product_id':anchor.id,'quantity':quantity})
    assert cache.sets==[]
    assert any(p['type']=='error' for _,p in cache.published)


@pytest.mark.asyncio
async def test_cart_existing_line_refreshes_current_price_and_name(catalog):
    from app.services.ai_cart_service import AICartService
    from tests.test_ai_cart_service import FakeCache
    sessions,(anchor,*_)=catalog
    cache=FakeCache({'items':[{'product_id':anchor.id,'name':'Old name','price':'1.00','quantity':1}]})
    async with sessions() as db:
        await AICartService(db,cache,object()).handle_add_to_cart({'user_id':1,'product_id':anchor.id,'quantity':1})
    item=cache.sets[-1][1]['items'][0]
    assert item['name']==anchor.name and item['price']=='100.00' and item['quantity']==2


@pytest.mark.asyncio
async def test_cart_cannot_label_non_usd_catalog_price_as_dollars(catalog):
    from app.services.ai_cart_service import AICartService
    from tests.test_ai_cart_service import FakeCache
    sessions,(anchor,*_)=catalog
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==anchor.id).values(currency='EUR'));await db.commit()
    cache=FakeCache()
    async with sessions() as db:
        await AICartService(db,cache,object()).handle_add_to_cart({'user_id':1,'product_id':anchor.id})
    assert cache.sets==[] and cache._cart is None
    assert any('currency' in p.get('content','') for _,p in cache.published)
    assert not any(p['type'] in {'success_text','cart_preview'} for _,p in cache.published)


@pytest.mark.asyncio
async def test_bundle_unrelated_primary_and_padding_fallback_abstain(catalog):
    sessions,(anchor,*others)=catalog
    engine=make_engine()
    engine.perform_hybrid_search_pure=AsyncMock(return_value=others)
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id.in_([p.id for p in others])).values(
            attributes={},name='Unrelated skincare makeup or second phone'))
        await db.commit()
    async with sessions() as db:
        assert await engine.generate_perfect_bundle(db,anchor)==[]
    assert engine.perform_hybrid_search_pure.call_count>=3


@pytest.mark.asyncio
async def test_bundle_cache_cannot_replay_revoked_relation(catalog):
    sessions,(anchor,kept,*_)=catalog
    cache=SimpleNamespace(get_json=AsyncMock(return_value=[kept.id]),set_json=AsyncMock())
    engine=make_engine(cache)
    engine.perform_hybrid_search_pure=AsyncMock(return_value=[kept])
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==kept.id).values(attributes={}))
        await db.commit()
    async with sessions() as db:
        assert await engine.generate_perfect_bundle(db,anchor)==[]


@pytest.mark.asyncio
async def test_bundle_timeout_fallback_requires_current_catalog_relation(catalog):
    sessions,(anchor,kept,unrelated,*_)=catalog
    engine=make_engine()
    engine.perform_hybrid_search_pure=AsyncMock(side_effect=TimeoutError())
    engine._get_emergency_fallback=AsyncMock(return_value=[kept,unrelated])
    async with sessions() as db:
        await db.execute(update(Product).where(Product.id==unrelated.id).values(attributes={}))
        await db.commit()
    async with sessions() as db:
        assert [p.id for p in await engine.generate_perfect_bundle(db,anchor)]==[kept.id]
