"""CAP06 cache IDs never supply current prices or relation evidence."""
import json
import os
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import delete,text,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_commerce_engine import AICommerceEngine,_cache_key
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
@pytest.mark.parametrize('change',['price','inactive','relation','deleted'])
async def test_bundle_actual_redis_snapshot_rehydrates_current_postgres_and_rejects_changes(real_cache,change):
    cache,_=real_cache;native=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(native,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            anchor=Product(sku=uuid4().hex,name='Device',description='',price=100,inventory=4)
            candidate=Product(sku=uuid4().hex,name='Case',description='',price=20,inventory=5,attributes={'complement_for_skus':json.dumps([anchor.sku])})
            db.add_all([anchor,candidate]);await db.commit();ids=[anchor.id,candidate.id]
        key=_cache_key('bundle',{'anchor_id':str(anchor.id),'version':9})
        await cache.set_json(key,[{'id':candidate.id,'price':1,'name':'Stale forged snapshot'}])
        engine=AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object(),cache_client=cache)
        engine.bootstrap=AsyncMock();engine.perform_hybrid_search_pure=AsyncMock(return_value=[])
        async with sessions() as db:
            result=await engine.generate_perfect_bundle(db,anchor)
            assert len(result)==1 and result[0].id==candidate.id and result[0].price==20 and result[0].name=='Case'
        engine.perform_hybrid_search_pure.assert_not_awaited()
        async with sessions() as db:
            if change=='deleted':await db.execute(delete(Product).where(Product.id==candidate.id))
            else:
                values={'price':{'price':90},'inactive':{'is_active':False},'relation':{'attributes':{}}}[change]
                await db.execute(update(Product).where(Product.id==candidate.id).values(**values))
            await db.commit()
        async with sessions() as db:
            assert await engine.generate_perfect_bundle(db,anchor)==[]
        # Reading a legacy snapshot is not authority to rewrite it or mutate a cart.
        assert (await cache.get_json(key))[0]['name']=='Stale forged snapshot'
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await native.dispose()
