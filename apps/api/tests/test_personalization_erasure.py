"""Real Redis generation prevents stale work after explicit full reset."""
from types import SimpleNamespace
from unittest.mock import AsyncMock,MagicMock
import pytest
from app.services.personalization_erasure import PersonalizationErasure
from app.services.personalization_fence import generation,write,key
from tests.test_customer_memory_postgres import memory_db
from tests.test_cart_persistence_outcomes import real_cache

@pytest.mark.asyncio
async def test_full_reset_owner_inventory_and_stale_generation(memory_db,real_cache):
    sessions,(uid,other)=memory_db;cache,_=real_cache
    from app.services.customer_memory_service import CustomerMemoryService
    expected=await generation(cache,uid)
    own=[f'ai:beh:u:{uid}:price_hist',f'ai:beh:u:{uid}:ghost_v2:old',f'dna:profile:{uid}:old',f'ai_session_v9:owner:{uid}:browser',f'airdeliver:v2:session:{uid}:chat_history',f'airdeliver:v2:session:{uid}:seen_products',f'airdeliver:freshness:{uid}',f'airdeliver:freshness:{uid}:shown_at']
    keep=[f'ai_cart:{uid}',f'ai:beh:u:{other}:price_hist',f'ai_session_v9:owner:{other}:browser']
    for item in own+keep:await cache.client.set(item,'sample')
    milvus=MagicMock();milvus.has_collection.return_value=True;milvus.query.return_value=[]
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        result=await PersonalizationErasure(db,cache,milvus).erase(uid)
        assert result['deleted'] and not result['incomplete_stores']
        assert not await service.enabled(uid)
    assert all([not await cache.client.exists(item) for item in own])
    assert all([await cache.client.exists(item) for item in keep])
    assert not await write(cache,uid,[['SET',own[0],'late']],expected)
    assert not await cache.client.exists(own[0])
    assert all(call.kwargs['filter']==f'user_id == {uid}' for call in milvus.delete.call_args_list)
    assert await write(cache,uid,[['SET',own[0],'new request']],await generation(cache,uid))

@pytest.mark.asyncio
async def test_incomplete_legacy_cleanup_reports_failure_and_keeps_barrier(memory_db,real_cache):
    sessions,(uid,_)=memory_db;cache,_=real_cache
    milvus=MagicMock();milvus.has_collection.side_effect=ConnectionError('controlled outage')
    async with sessions() as db:
        result=await PersonalizationErasure(db,cache,milvus).erase(uid)
        assert not result['deleted'] and result['incomplete_stores']
    assert await cache.client.exists(key(uid)+':reset_pending')
    assert not await write(cache,uid,[['SET',f'ai:beh:u:{uid}:price_hist','late']],'0')
    with pytest.raises(RuntimeError):await generation(cache,uid)

@pytest.mark.asyncio
async def test_erase_during_http_model_never_repersists_old_context(memory_db,real_cache):
    from app.services.neural_core_service import NeuralCoreService,NeuralCoreResponse
    sessions,(uid,_)=memory_db;cache,_=real_cache
    svc=NeuralCoreService(object(),cache)
    milvus=MagicMock();milvus.has_collection.return_value=False
    async with sessions() as db:
        async def model(*args,**kwargs):
            from app.services.neural_core_service import SessionMemory
            await svc._persist_session(f'owner:{uid}:browser',SessionMemory(user_name='Local'))
            async with sessions() as writer:assert (await PersonalizationErasure(writer,cache,milvus).erase(uid))['deleted']
            return NeuralCoreResponse(text='old reply',response_kind='clarification',confidence=1,explain='test',telemetry={'intent':'SOCIAL_CHAT','entities':[],'turn':0})
        svc._handle_message_with_context=model
        result=await svc.handle_message(db,'test',SimpleNamespace(id=uid,full_name='Local'),f'owner:{uid}:browser')
    assert result.response_kind=='system_notice' and 'reset' in result.text
    assert not await cache.client.keys(f'ai_session_v9:owner:{uid}:*')

@pytest.mark.asyncio
async def test_pending_behavior_packet_stops_after_learning_off_or_full_erase(memory_db,real_cache,monkeypatch):
    import asyncio,time
    from app.services.ai_behavior_engine import BehaviorEngine,ACTION_MAP
    from app.services.customer_memory_service import CustomerMemoryService
    import app.db.session as database
    sessions,(uid,_)=memory_db;cache,_=real_cache
    monkeypatch.setattr(database,'AsyncSessionFactory',sessions)
    engine=object.__new__(BehaviorEngine);engine.cache=cache;engine.net_config=SimpleNamespace(supported_dims={'dim_4':4});engine.embedding_sources={'dim_4':'test'};engine._background_tasks=set();engine._dream_future=AsyncMock()
    async with sessions() as db:await CustomerMemoryService(db).set_consent(uid,True)
    stamp=await engine._learning_generation(uid)
    event=dict(u=uid,d=4,a=ACTION_MAP['view'],v=[.1,.2,.3,.4],ts=time.time(),privacy=stamp,price=20.,item_id=1)
    async with sessions() as db:await CustomerMemoryService(db).set_consent(uid,False)
    await engine._consolidate_memory([event]);engine._dream_future.assert_not_awaited()
    assert not await cache.client.keys(f'ai:beh:u:{uid}:*')
    async with sessions() as db:await CustomerMemoryService(db).set_consent(uid,True)
    fresh=await engine._learning_generation(uid)
    assert not await engine._commit_learning(uid,stamp,[['SET',f'ai:beh:u:{uid}:late','1']])
    async with sessions() as db:
        vectors=MagicMock();vectors.has_collection.return_value=False
        assert (await PersonalizationErasure(db,cache,vectors).erase(uid))['deleted']
    assert not await engine._commit_learning(uid,fresh,[['SET',f'ai:beh:u:{uid}:late','1']])
    assert not await cache.client.exists(f'ai:beh:u:{uid}:late')

@pytest.mark.asyncio
async def test_mounted_reset_is_self_only_and_partial_storage_failure_not_success(memory_db,real_cache,monkeypatch):
    from app.main import app
    from app.api import deps
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    from app.services import ai_commerce_engine
    from httpx import AsyncClient,ASGITransport
    sessions,(uid,other)=memory_db;cache,_=real_cache
    async def db_session():
        async with sessions() as db:yield db
    app.dependency_overrides[get_async_session]=db_session
    app.dependency_overrides[get_cache_from_request]=lambda:cache
    app.dependency_overrides[deps.get_current_active_user]=lambda:SimpleNamespace(id=uid)
    vectors=MagicMock();vectors.has_collection.return_value=False
    monkeypatch.setattr(ai_commerce_engine,'get_milvus_client',lambda settings:vectors)
    await cache.client.set(f'ai:beh:u:{other}:price_hist','other')
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            response=await client.delete(f'/api/v1/users/me/memory/personalization?user_id={other}')
            assert response.status_code==200 and response.json()['deleted'] is True
            assert response.headers['cache-control']=='no-store'
            assert await cache.client.get(f'ai:beh:u:{other}:price_hist')=='other'
            vectors.has_collection.side_effect=ConnectionError('controlled legacy outage')
            response=await client.delete('/api/v1/users/me/memory/personalization')
            assert response.status_code==503 and response.json()['deleted'] is False
    finally:app.dependency_overrides.clear()
