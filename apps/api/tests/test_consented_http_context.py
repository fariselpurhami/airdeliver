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
@pytest.mark.parametrize('mode',['enabled','other_owner','revoked','feature_off','revoked_during_model'])
async def test_http_saved_context_is_owner_bound_consent_gated_and_rechecked(memory_db,real_cache,monkeypatch,mode):
    sessions,(uid,other)=memory_db;cache,_=real_cache
    extractor=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        await service.collect(uid,'I prefer blue',extractor)
        if mode=='revoked':await service.set_consent(uid,False)
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
        assert context==(['Customer explicitly prefers color: blue'] if mode in {'enabled','revoked_during_model'} else [])
        if mode=='revoked_during_model':
            assert response.json()['response_kind']=='system_notice'
            # The rejected personalized response is not retained in Redis.
            assert not await cache.client.keys('ai_session_v9:*')
        else:assert response.json()['response_kind']=='clarification'
    finally:app.dependency_overrides.clear()
