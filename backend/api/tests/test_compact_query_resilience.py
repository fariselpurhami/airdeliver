"""Real Redis admission across independent clients; no external providers."""
import asyncio,json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from redis.asyncio import Redis
from tests.test_cart_persistence_outcomes import real_cache
from app.services.shared_provider_admission import shared_provider_slot,SharedProviderBudgetError,provider_turn_budget
from app.services.sales_response_service import SalesResponseService,SalesResponseRequest
from app.services.shopping_discovery import ShoppingBrief

@pytest.mark.asyncio
async def test_shared_clients_serialize_reconcile_and_limit(real_cache):
    cache,_=real_cache
    uri=cache.client.connection_pool.connection_kwargs
    other=Redis(host=uri['host'],port=uri['port'],decode_responses=True)
    peak=active=0
    async def run(client):
        nonlocal active,peak
        async with shared_provider_slot('offline-cross-process',[],{},100,.5,client=client,limit=1000) as reservation:
            active+=1;peak=max(peak,active)
            await asyncio.sleep(.02)
            reservation.observe(SimpleNamespace(usage=SimpleNamespace(total_tokens=450)))
            active-=1
    try:
        await asyncio.gather(run(cache.client),run(other))
        assert peak==1
        with pytest.raises(SharedProviderBudgetError):await run(other)
    finally:await other.aclose()

@pytest.mark.asyncio
async def test_shared_cooldown_unknown_cost_and_cancel_release(real_cache):
    cache,_=real_cache;client=cache.client
    async with shared_provider_slot('offline-quota',[],{},100,client=client) as reservation:
        await reservation.quota(.15)
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot('offline-quota',[],{},100,client=client):pass
    entered=asyncio.Event()
    async def wait():
        async with shared_provider_slot('offline-cancel',[],{},100,client=client):
            entered.set();await asyncio.Event().wait()
    task=asyncio.create_task(wait());await entered.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    async with shared_provider_slot('offline-cancel',[],{},100,client=client):pass

@pytest.mark.asyncio
async def test_turn_call_cap_has_no_seventh_transport():
    async with provider_turn_budget():
        for _ in range(6):
            async with shared_provider_slot('offline-turn',[],{},1):pass
        with pytest.raises(SharedProviderBudgetError):
            async with shared_provider_slot('offline-turn',[],{},1):pytest.fail('seventh')

@pytest.mark.asyncio
@pytest.mark.parametrize('query',[
    'laptop for editing with 32GB RAM under $1200',
    'shoes in size 48, only linen material',
    'unrecorded industrial product category',
    'wirless hedphones with missing codec',
    'compare Alpha and Beta and unknown third item',
    'شيء مناسب للاستخدام غير المعروف',
])
async def test_empty_classes_use_tiny_model_authored_reviewed_reply(query):
    seen=[]
    async def infer(messages):
        seen.append(messages)
        if len(seen)==1:return json.dumps(dict(text='No matching candidates were found in these current results. Would you like to broaden the search?',product_ids=[],claims=[]))
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(SalesResponseRequest(message=query,products=(),brief=ShoppingBrief(),mode='catalog_results',intent='PRODUCT_SEARCH'))
    assert result.response_kind=='catalog_results' and result.products==[] and len(seen)==2
    assert len(seen[0][0]['content'])<800 and len(seen[1][0]['content'])<600
    assert json.loads(seen[0][1]['content'])['customer_message']==query

@pytest.mark.asyncio
@pytest.mark.parametrize('failure',['429','invented','review','long'])
async def test_empty_failure_modes_still_fail_closed(failure):
    if failure=='429':infer=AsyncMock(side_effect=RuntimeError('quota'))
    else:
        draft=dict(text='No matches in these results. Broaden the search?',product_ids=[99] if failure=='invented' else [],claims=[])
        if failure=='long':draft['text']='x'*2001
        verdict=dict(supported=failure!='review',all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
        infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(verdict)])
    response=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(SalesResponseRequest(message='unknown',products=(),brief=ShoppingBrief(),mode='catalog_results',intent='PRODUCT_SEARCH'))
    assert response.response_kind=='system_notice' and response.products==[]

@pytest.mark.asyncio
async def test_single_oversize_and_actual_quota_do_not_silently_retry(real_cache):
    cache,_=real_cache
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot('offline-huge',[{'content':'x'*30000}],{},100,client=cache.client):pytest.fail('oversize sent')
    # Even when actual usage exceeds the estimate, later requests are withheld.
    async with shared_provider_slot('offline-actual',[],{},100,client=cache.client,limit=1000) as reservation:
        reservation.observe(SimpleNamespace(usage=SimpleNamespace(total_tokens=1200)))
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot('offline-actual',[],{},100,client=cache.client,limit=1000):pytest.fail('over quota')

@pytest.mark.asyncio
async def test_configured_redis_disconnect_fails_closed(real_cache):
    cache,process=real_cache
    process.terminate();await asyncio.to_thread(process.wait,3)
    with pytest.raises(Exception):
        async with shared_provider_slot('offline-disconnected',[],{},100,client=cache.client):pytest.fail('provider permitted')

@pytest.mark.asyncio
async def test_native_free_and_core_adapters_share_redis_gate(real_cache,monkeypatch):
    from app.services import shared_provider_admission as shared
    from app.services.free_llm_service import FreeLLMService
    from app.services.provider_budget import complete
    cache,_=real_cache;values=cache.client.connection_pool.connection_kwargs
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:SimpleNamespace(REDIS_URL=f"redis://127.0.0.1:{values['port']}/0",PROVIDER_TPM_BUDGET=8000))
    svc=object.__new__(FreeLLMService);svc.__init__();active=peak=0
    async def create(**kwargs):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        await asyncio.sleep(.01);active-=1
        return SimpleNamespace(usage=SimpleNamespace(total_tokens=100),choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))])
    svc._get_client=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    await asyncio.gather(svc._chat_completion(model='offline-real-shared',messages=[{'role':'user','content':'private'}],timeout_seconds=1),complete(create,model='offline-real-shared',messages=[],response_format={},timeout=1))
    assert peak==1
    keys=await cache.client.keys('airdeliver:provider:*')
    for key in keys:
        if await cache.client.type(key)=='zset':assert 'private' not in str(await cache.client.zrange(key,0,-1))
