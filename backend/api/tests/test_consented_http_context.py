"""Canonical consented context through real SQL/Redis and mounted HTTP."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.core.config import get_core_settings
from app.services.customer_memory_service import CustomerMemoryService
from app.services.neural_core_service import NeuralCoreService,get_neural_core_service
from tests.test_customer_memory_postgres import memory_db
from tests.test_cart_persistence_outcomes import real_cache


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['enabled','other_owner','revoked','feature_off','revoked_during_model','learning_off','off_during_model'])
async def test_http_saved_context_is_owner_bound_consent_gated_and_rechecked(memory_db,real_cache,monkeypatch,mode):
    sessions,(uid,other)=memory_db;cache,_=real_cache
    extractor=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        await service.collect(uid,'I prefer blue',extractor)
        if mode=='revoked':await service.erase_preferences(uid)
        if mode=='learning_off':await service.set_consent(uid,False)
    if mode=='feature_off':monkeypatch.setattr(get_core_settings(),'CUSTOMER_MEMORY_ENABLED',False)
    active_uid=other if mode=='other_owner' else uid
    svc=NeuralCoreService(object(),cache);svc.is_healthy=True;svc.configuration_error=False
    seen=[]
    async def infer(messages):
        if 'primary cognitive routing' in messages[0]['content']:
            return json.dumps({'intent':'GIFT_DISCOVERY','brief':{'recipient':'wife'}})
        payload=json.loads(messages[1]['content']);seen.append(payload)
        if 'catalog_evidence' in payload:
            if mode=='revoked_during_model':
                async with sessions() as revoke:await CustomerMemoryService(revoke).erase_preferences(uid)
            if mode=='off_during_model':
                async with sessions() as revoke:await CustomerMemoryService(revoke).set_consent(uid,False)
            return json.dumps({'text':'What occasion and product category do you have in mind, and what is your budget?','product_ids':[],'claims':[]})
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    svc._execute_llm_inference=infer
    from app.main import app
    from app.api import deps
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    from httpx import AsyncClient,ASGITransport
    async def get_db():
        async with sessions() as db:yield db
    app.dependency_overrides[get_async_session]=get_db
    app.dependency_overrides[get_neural_core_service]=lambda:svc
    app.dependency_overrides[get_cache_from_request]=lambda:cache
    app.dependency_overrides[deps.get_optional_current_user]=lambda:SimpleNamespace(id=active_uid,full_name='Local')
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/ai-support/chat',json={'message':'I want a gift for my wife','session_id':'consented-http-test'})
        assert response.status_code==200,response.text
        context=seen[0]['request_evidence'].get('consented_saved_preferences',[])
        assert context==(['Customer explicitly prefers color: blue'] if mode in {'enabled','revoked_during_model','learning_off','off_during_model'} else [])
        if mode=='revoked_during_model':
            assert response.json()['response_kind']=='system_notice'
            # The rejected personalized response is not retained in Redis.
            assert not await cache.client.keys('ai_session_v9:*')
        else:assert response.json()['response_kind']=='clarification'
    finally:app.dependency_overrides.clear()

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['enabled','no_consent','provider_failure','revoked_during_extract'])
async def test_http_current_customer_preference_collection_preserves_consent_and_response(memory_db,real_cache,monkeypatch,mode):
    sessions,(uid,_)=memory_db;cache,_=real_cache
    async with sessions() as db:
        if mode!='no_consent':await CustomerMemoryService(db).set_consent(uid,True)
    svc=NeuralCoreService(object(),cache);svc.is_healthy=True;svc.configuration_error=False
    async def infer(messages):
        if 'primary cognitive routing' in messages[0]['content']:return json.dumps({'intent':'GIFT_DISCOVERY','brief':{}})
        if 'catalog_evidence' in json.loads(messages[1]['content']):return json.dumps({'text':'Which product category are you considering?','product_ids':[],'claims':[]})
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    svc._execute_llm_inference=infer
    calls=[]
    async def extract(self,statement,catalog):
        calls.append(statement)
        if mode=='provider_failure':raise ConnectionError('controlled preference extraction outage')
        if mode=='revoked_during_extract':
            async with sessions() as db:await CustomerMemoryService(db).erase_preferences(uid)
        return {'category':'color','value':'blue','evidence':'I prefer blue'}
    from app.services.free_llm_service import FreeLLMService
    monkeypatch.setattr(FreeLLMService,'extract_shopping_preferences_batch',extract)
    from app.main import app
    from app.api import deps
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    from httpx import AsyncClient,ASGITransport
    async def get_db():
        async with sessions() as db:yield db
    app.dependency_overrides[get_async_session]=get_db
    app.dependency_overrides[get_neural_core_service]=lambda:svc
    app.dependency_overrides[get_cache_from_request]=lambda:cache
    app.dependency_overrides[deps.get_optional_current_user]=lambda:SimpleNamespace(id=uid,full_name='Local')
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/ai-support/chat',json={'message':'I prefer blue','session_id':'http-pref-collect'})
        assert response.status_code==200 and response.json()['response_kind']=='clarification'
        assert calls==([] if mode=='no_consent' else ['I prefer blue'])
        async with sessions() as db:
            preferences=await CustomerMemoryService(db).recall(uid)
            assert preferences==(['Customer explicitly prefers color: blue'] if mode=='enabled' else [])
        history=await cache.get_json_required(svc._get_session_key(f'owner:{uid}:'+__import__('hashlib').sha256(b'http-pref-collect').hexdigest()))
        assert history['history'][-1]['content']==response.json()['text']
    finally:app.dependency_overrides.clear()

@pytest.mark.asyncio
@pytest.mark.parametrize('route',['setup','research'])
@pytest.mark.parametrize('mode',['enabled','other_owner','revoked_during_model'])
async def test_special_paths_receive_separate_consented_hints_and_recheck_before_publish(memory_db,real_cache,monkeypatch,route,mode):
    sessions,(uid,other)=memory_db;cache,_=real_cache
    async with sessions() as db:
        memory=CustomerMemoryService(db);await memory.set_consent(uid,True)
        await memory.collect(uid,'I prefer blue',SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'})))
    svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(return_value=[])),cache);svc.is_healthy=True;svc.configuration_error=False
    seen=[]
    async def infer(messages):
        prompt=messages[0]['content']
        if 'primary cognitive routing' in prompt:
            return json.dumps({'intent':'SETUP_DISCOVERY' if route=='setup' else 'PRODUCT_SEARCH','search_subject':'desk','targets':[] if route=='setup' else [{'product_name':'desk'}],'shopping_task':'search' if route=='setup' else 'specifications'})
        payload=json.loads(messages[1]['content'])
        if 'Plan generic component' in prompt or 'Extract source-backed' in prompt:
            seen.append(payload)
            if mode=='revoked_during_model':
                async with sessions() as db:await CustomerMemoryService(db).erase_preferences(uid)
        if 'Plan generic component' in prompt:return json.dumps({'components':['desk']})
        if 'Review a generic setup' in prompt:return json.dumps({'appropriate':True,'no_invented_products':True})
        if 'Extract source-backed' in prompt:return json.dumps({'covered_targets':['desk'],'facts':[{'label':'Material','quote':'desk is wood','source':0}]})
        if 'Review source extraction' in prompt:return json.dumps({'supported':True,'exact_model':True,'product_information_only':True})
        if 'catalog_evidence' in payload:return json.dumps({'text':'No current card could be verified.','product_ids':[],'claims':[]})
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    svc._execute_llm_inference=infer
    from app.services import product_knowledge_service
    queries=[]
    async def lookup(query):
        queries.append(query);return [{'url':'https://maker.example/spec','text':'desk is wood'}]
    monkeypatch.setattr(product_knowledge_service,'lookup_product_sources',lookup)
    from app.main import app
    from app.api import deps
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    from httpx import AsyncClient,ASGITransport
    async def get_db():
        async with sessions() as db:yield db
    app.dependency_overrides[get_async_session]=get_db
    app.dependency_overrides[get_neural_core_service]=lambda:svc
    app.dependency_overrides[get_cache_from_request]=lambda:cache
    app.dependency_overrides[deps.get_optional_current_user]=lambda:SimpleNamespace(id=other if mode=='other_owner' else uid,full_name='Local')
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/ai-support/chat',json={'message':'desk setup' if route=='setup' else 'desk specifications','session_id':'special-context-test'})
        assert response.status_code==200,response.text
        assert seen and seen[0]['consented_saved_preferences']==([] if mode=='other_owner' else ['Customer explicitly prefers color: blue'])
        assert all('blue' not in query for query in queries)
        if mode=='revoked_during_model':
            assert response.json()['response_kind']=='system_notice'
            assert not await cache.client.keys('ai_session_v9:*')
        else:assert response.json()['response_kind']!='system_notice'
    finally:app.dependency_overrides.clear()
