from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.services.cart_lifecycle_review import prepare,confirm
from app.services.ai_cart_service import AICartService
from app.services.neural_core_service import NeuralCoreService,RouterDecision
from tests.test_cart_persistence_outcomes import real_cache

async def seed(cache,user=17):
    value={'items':[{'product_id':7,'name':'Fixture','quantity':1,'price':'20'}],'total':'20','updated_at':'fixture'}
    await cache.set_json_required(f'ai_cart:{user}',value,ttl=60)
    return value

@pytest.mark.asyncio
async def test_review_no_mutation_owner_bound_expiring_and_one_shot(real_cache):
    cache,_=real_cache;before=await seed(cache)
    payload=await prepare(cache,17,'clear')
    assert await cache.get_json_required('ai_cart:17')==before
    service=AICartService(None,cache,None)
    with pytest.raises(HTTPException):await confirm(service,18,payload['review_id'])
    assert await confirm(service,17,payload['review_id'])=={'status':'cleared'}
    assert await cache.get_json_required('ai_cart:17') is None
    with pytest.raises(HTTPException):await confirm(service,17,payload['review_id'])
    with pytest.raises(HTTPException):await confirm(service,17,str(uuid4()))

@pytest.mark.asyncio
async def test_changed_cart_rejects_and_consumes_review(real_cache):
    cache,_=real_cache;await seed(cache);payload=await prepare(cache,17,'clear')
    newer=await seed(cache);newer['items'][0]['quantity']=2;newer['total']='40';await cache.set_json_required('ai_cart:17',newer)
    with pytest.raises(HTTPException):await confirm(AICartService(None,cache,None),17,payload['review_id'])
    assert await cache.get_json_required('ai_cart:17')==newer

@pytest.mark.asyncio
async def test_save_passes_exact_snapshot_no_model_execution(real_cache):
    cache,_=real_cache;before=await seed(cache)
    service=NeuralCoreService(object(),cache)
    assert (await service._handle_cart_lifecycle_review(RouterDecision(intent='CART_SAVE'),None)).action is None
    result=await service._handle_cart_lifecycle_review(RouterDecision(intent='CART_SAVE'),SimpleNamespace(id=17))
    assert result.action.action=='review_cart_lifecycle'
    assert 'cancelled' in result.text and await cache.get_json_required('ai_cart:17')==before
    cart=AICartService(None,cache,None);cart.handle_save_cart=AsyncMock(return_value={'status':'saved'})
    await confirm(cart,17,result.action.payload.review_id)
    assert cart.handle_save_cart.await_args.args[0]['expected_snapshot']==before

@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['clear','save'])
async def test_actual_http_sql_redis_review_effects_and_owner_gate(real_cache,operation):
    import os,json
    from httpx import AsyncClient,ASGITransport
    from sqlalchemy import select,delete
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.main import app
    from app.api import deps
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    from app.services.neural_core_service import get_neural_core_service
    from app.api.v1.endpoints.ai_ordering import get_ai_cart_service
    from app.models.user import User
    from app.models.product import Product
    from app.models.order import Order,OrderItem
    from app.models.enums import OrderStatus
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
    uid=pid=None
    try:
        async with sessions() as db:
            user=User(email=uuid4().hex+'@example.com',hashed_password='fixture');product=Product(sku=uuid4().hex,name='Lifecycle fixture',description='',price=20,inventory=5,currency='USD')
            db.add_all([user,product]);await db.commit();uid=user.id;pid=product.id
            pending=Order(user_id=uid,status=OrderStatus.PENDING,total_price=20);db.add(pending);await db.commit();pending_id=pending.id
        await cache.set_json_required(f'ai_cart:{uid}',{'items':[{'product_id':pid,'name':'Lifecycle fixture','quantity':1,'price':'20'}],'total':'20','updated_at':'fixture'})
        service=NeuralCoreService(object(),cache);service.is_healthy=True;service.configuration_error=False
        service._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'CART_'+operation.upper()}))
        async def get_db():
            async with sessions() as db:yield db
        async def get_cart():
            async with sessions() as db:yield AICartService(db,cache,None)
        app.dependency_overrides[get_async_session]=get_db
        app.dependency_overrides[get_cache_from_request]=lambda:cache
        app.dependency_overrides[get_neural_core_service]=lambda:service
        app.dependency_overrides[deps.get_optional_current_user]=lambda:user
        app.dependency_overrides[deps.get_current_active_user]=lambda:user
        app.dependency_overrides[get_ai_cart_service]=get_cart
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/ai-support/chat',json={'message':operation+' my cart','session_id':'lifecycle-'+uuid4().hex})
            assert response.status_code==200,response.text
            review=response.json()['action']['payload']['review_id']
            assert await cache.get_json_required(f'ai_cart:{uid}') is not None
            app.dependency_overrides[deps.get_current_active_user]=lambda:SimpleNamespace(id=uid+100000)
            assert (await client.post('/api/v1/ai-ordering/cart/review/confirm',json={'review_id':review})).status_code==409
            app.dependency_overrides[deps.get_current_active_user]=lambda:user
            result=await client.post('/api/v1/ai-ordering/cart/review/confirm',json={'review_id':review})
            assert result.status_code==200,result.text
            assert result.json()['status']==('cleared' if operation=='clear' else 'saved')
            assert (await client.post('/api/v1/ai-ordering/cart/review/confirm',json={'review_id':review})).status_code==409
        assert await cache.get_json_required(f'ai_cart:{uid}') is None
        async with sessions() as db:
            assert (await db.get(Order,pending_id)).status==OrderStatus.PENDING
            saved=(await db.execute(select(Order).where(Order.user_id==uid,Order.delivery_address=='Saved List'))).scalars().all()
            assert len(saved)==(1 if operation=='save' else 0)
            if saved:assert saved[0].status==OrderStatus.CANCELLED and not saved[0].is_paid
    finally:
        app.dependency_overrides.clear()
        if uid:
            async with sessions() as db:
                await db.execute(delete(OrderItem).where(OrderItem.order_id.in_(select(Order.id).where(Order.user_id==uid))))
                await db.execute(delete(Order).where(Order.user_id==uid));await db.execute(delete(Product).where(Product.id==pid));await db.execute(delete(User).where(User.id==uid));await db.commit()
        await engine.dispose()

@pytest.mark.asyncio
async def test_concurrent_confirm_one_effect_expiry_and_disconnect_fail_closed(real_cache):
    import asyncio
    cache,process=real_cache;await seed(cache)
    payload=await prepare(cache,17,'clear');service=AICartService(None,cache,None)
    results=await asyncio.gather(*(confirm(service,17,payload['review_id']) for _ in range(2)),return_exceptions=True)
    assert sum(isinstance(r,dict) and r.get('status')=='cleared' for r in results)==1
    await seed(cache);payload=await prepare(cache,17,'clear')
    key=f"cart_lifecycle_review:17:{payload['review_id']}"
    assert 0<await cache.client.ttl(key)<=300
    await cache.client.pexpire(key,1);await asyncio.sleep(.02)
    with pytest.raises(HTTPException):await confirm(service,17,payload['review_id'])
    assert await cache.get_json_required('ai_cart:17') is not None
    process.terminate();await asyncio.to_thread(process.wait,3)
    with pytest.raises(Exception):await prepare(cache,17,'clear')
