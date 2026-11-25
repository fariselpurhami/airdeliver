"""Current PostgreSQL + real Redis + worker/UI boundary. Model transport only controlled."""
import json
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete, update, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.product import Product
from app.services.cart_sales_service import CartSalesService
from tests.test_cart_persistence_outcomes import real_cache
from worker_entrypoint import WorkerRuntime

pytestmark = pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'), reason='migrated disposable PostgreSQL required')


def model_transport(hook=None, rejected=False):
    calls=[]
    async def infer(messages):
        data=json.loads(messages[1]['content']);calls.append(data)
        if 'catalog_evidence' in data:
            if hook: await hook()
            card=data['catalog_evidence'][0]
            return json.dumps({'text':card['name']+' is an optional related local catalog item. Merchant stock and compatibility are unverified.',
                'product_ids':[card['id']], 'claims':[{'product_id':card['id'],'field':'name','value':card['name']}]})
        return json.dumps(dict(supported=not rejected,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    return SimpleNamespace(infer_sales_json=infer), calls


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['added','removed'])
async def test_real_worker_model_cards_current_rows_and_no_cart_mutation(real_cache, operation):
    cache,_=real_cache
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
    ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            anchor=Product(description="",sku=uuid4().hex,name='Anchor',category='devices',price=100,inventory=10,currency='USD')
            candidate=Product(description="",sku=uuid4().hex,name='Current candidate',category='devices',price=100 if operation=='removed' else 20,inventory=8,currency='USD',attributes={'complement_for_skus':json.dumps([anchor.sku])})
            demo=Product(description="",sku=uuid4().hex,name='Demo',category='devices',price=20,inventory=10,attributes={'_seed_dataset':'airdeliver-demo-v1','complement_for_skus':json.dumps([anchor.sku])})
            db.add_all([anchor,candidate,demo]);await db.commit();ids=[anchor.id,candidate.id,demo.id]
        items=[{'product_id':anchor.id,'name':'Anchor','price':'100','quantity':1}] if operation=='added' else []
        await cache.set_json_required('ai_cart:71',{'items':items})
        before=await cache.get_json_required('ai_cart:71');published=[]
        original=cache.publish
        async def capture(channel,payload):
            published.append(json.loads(payload));await original(channel,payload)
        cache.publish=capture
        llm,calls=model_transport()
        retrieval=SimpleNamespace(generate_perfect_bundle=AsyncMock(return_value=[candidate,demo]),find_genius_alternatives=AsyncMock(return_value=[candidate,demo]))
        runtime=WorkerRuntime.__new__(WorkerRuntime);runtime.wait_for_readiness=AsyncMock()
        runtime.services=SimpleNamespace(session_maker=sessions,cache=cache,rabbitmq=object(),commerce=retrieval,llm=llm)
        await runtime.cart_recommendation_handler_impl({'user_id':71,'product_id':anchor.id,'operation':operation,'removal_reason':'too costly' if operation=='removed' else None})
        assert await cache.get_json_required('ai_cart:71')==before
        assert len(published)==1 and published[0]['type']=='product_carousel'
        assert [p['id'] for p in published[0]['products']]==[candidate.id]
        assert published[0]['content'].startswith('Current candidate')
        assert calls[0]['request_evidence']['cart_event']==operation
        assert calls[0]['request_evidence']['customer_stated_removal_reason']==('too costly' if operation=='removed' else None)
        assert calls[0]['catalog_evidence'][0]['evidence_kind']=='local_catalog'
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['added','removed'])
@pytest.mark.parametrize('change', ['price','stock','inactive','relation','deleted','cart','rejected','offline','timeout','cancel'])
async def test_inflight_change_or_provider_failure_withholds_optional_advice(real_cache, change,operation):
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            anchor=Product(description="",sku=uuid4().hex,name='Anchor',category='devices',price=100,inventory=10,currency='USD')
            candidate=Product(description="",sku=uuid4().hex,name='Case',category='devices',price=100 if operation=='removed' else 20,inventory=8,currency='USD',attributes={'complement_for_skus':json.dumps([anchor.sku])})
            db.add_all([anchor,candidate]);await db.commit();ids=[anchor.id,candidate.id]
        await cache.set_json_required('ai_cart:72',{'items':[{'product_id':anchor.id,'name':'Anchor','price':'100','quantity':1}] if operation=='added' else []})
        published=[]
        async def capture(channel,payload):published.append(json.loads(payload))
        cache.publish=capture
        async def hook():
            if change=='cart':
                await cache.set_json_required('ai_cart:72',{'items':[] if operation=='added' else [{'product_id':anchor.id,'name':'Anchor','price':'100','quantity':1}]});return
            if change=='cancel':
                import asyncio
                raise asyncio.CancelledError()
            if change=='timeout':
                raise TimeoutError('controlled provider deadline')
            if change in {'rejected','offline'}:return
            async with sessions() as db:
                if change=='deleted':await db.execute(delete(Product).where(Product.id==candidate.id))
                else:
                    values={'price':{'price':21},'stock':{'inventory':0},'inactive':{'is_active':False},'relation':{'category':'unrelated'} if operation=='removed' else {'attributes':{}}}[change]
                    await db.execute(update(Product).where(Product.id==candidate.id).values(**values))
                await db.commit()
        llm,calls=model_transport(hook,rejected=change=='rejected')
        if change=='offline':llm.infer_sales_json=AsyncMock(side_effect=ConnectionError('provider unavailable'))
        runtime=WorkerRuntime.__new__(WorkerRuntime);runtime.wait_for_readiness=AsyncMock()
        runtime.services=SimpleNamespace(session_maker=sessions,cache=cache,rabbitmq=object(),commerce=SimpleNamespace(generate_perfect_bundle=AsyncMock(return_value=[candidate]),find_genius_alternatives=AsyncMock(return_value=[candidate])),llm=llm)
        if change=='cancel':
            import asyncio
            with pytest.raises(asyncio.CancelledError):await runtime.cart_recommendation_handler_impl({'user_id':72,'product_id':anchor.id,'operation':operation})
        else:await runtime.cart_recommendation_handler_impl({'user_id':72,'product_id':anchor.id,'operation':operation})
        assert published==[]
        cart=await cache.get_json_required('ai_cart:72')
        assert len(cart['items'])==((0 if operation=='added' else 1) if change=='cart' else (1 if operation=='added' else 0))
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_confirmed_remove_forwards_explicit_reason_only_to_optional_worker(real_cache):
    from app.services.ai_cart_service import AICartService
    cache,_=real_cache
    await cache.set_json_required('ai_cart:75',{'items':[{'product_id':7,'name':'Fixture','price':'20','quantity':1}]})
    published=[]
    async def publish(payload,key,**kwargs):
        published.append((payload,key));return SimpleNamespace(is_success=True)
    service=AICartService(None,cache,SimpleNamespace(publish=publish))
    await service.handle_remove_from_cart({'user_id':75,'product_id':7,'removal_reason':'too costly'})
    assert (await cache.get_json_required('ai_cart:75'))['items']==[]
    events=[payload for payload,key in published if key=='airdeliver.ai.cart.recommendation']
    assert len(events)==1 and events[0]['removal_reason']=='too costly'
    assert events[0]['operation']=='removed'
    assert all('removal_reason' not in payload for payload,key in published if key!='airdeliver.ai.cart.recommendation')


@pytest.mark.asyncio
async def test_add_optional_event_preserves_legacy_shape_without_null_reason():
    from app.services.ai_cart_service import AICartService
    published=[]
    async def publish(payload,key,**kwargs):
        published.append(payload);return SimpleNamespace(is_success=True)
    await AICartService(None,None,SimpleNamespace(publish=publish))._request_optional_recommendations(17,7,'added','must be stripped')
    assert published==[{'version':1,'user_id':17,'product_id':7,'operation':'added'}]

@pytest.mark.asyncio
@pytest.mark.parametrize('change',['excluded','anchor_deleted','anchor_category','anchor_price','currency'])
async def test_removed_recovery_current_anchor_and_owner_cart_exclusions(real_cache,change):
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            anchor=Product(description='',sku=uuid4().hex,name='Removed',category='devices',price=100,inventory=0,currency='USD')
            candidate=Product(description='',sku=uuid4().hex,name='Alternative',category='devices',price=100,inventory=4,currency='USD')
            db.add_all([anchor,candidate]);await db.commit();ids=[anchor.id,candidate.id]
        items=[{'product_id':candidate.id,'name':'Alternative','price':'100','quantity':1}] if change=='excluded' else []
        await cache.set_json_required('ai_cart:77',{'items':items});before=await cache.get_json_required('ai_cart:77');published=[]
        async def publish(channel,payload):published.append(json.loads(payload))
        cache.publish=publish
        async def hook():
            async with sessions() as db:
                if change=='anchor_deleted':await db.execute(delete(Product).where(Product.id==anchor.id))
                elif change=='anchor_category':await db.execute(update(Product).where(Product.id==anchor.id).values(category='unrelated'))
                elif change=='anchor_price':await db.execute(update(Product).where(Product.id==anchor.id).values(price=10))
                elif change=='currency':await db.execute(update(Product).where(Product.id==candidate.id).values(currency='EUR'))
                await db.commit()
        llm,calls=model_transport(hook)
        runtime=WorkerRuntime.__new__(WorkerRuntime);runtime.wait_for_readiness=AsyncMock()
        runtime.services=SimpleNamespace(session_maker=sessions,cache=cache,rabbitmq=object(),commerce=SimpleNamespace(find_genius_alternatives=AsyncMock(return_value=[candidate])),llm=llm)
        await runtime.cart_recommendation_handler_impl({'user_id':77,'product_id':anchor.id,'operation':'removed'})
        assert published==[] and await cache.get_json_required('ai_cart:77')==before
        if change=='excluded':assert not calls
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
