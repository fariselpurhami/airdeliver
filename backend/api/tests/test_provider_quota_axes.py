"""Real Redis quota dimensions. No outbound provider traffic or cap changes."""
import asyncio
import hashlib
from types import SimpleNamespace
import pytest
from app.services.shared_provider_admission import shared_provider_slot,SharedProviderBudgetError,estimated_tokens
from tests.test_cart_persistence_outcomes import real_cache


def config(**axes):
    values=dict(PROVIDER_CAPACITY_PLAN='free',PROVIDER_TPM_BUDGET=5000,REDIS_URL=None)
    values.update(axes)
    return SimpleNamespace(**values)

def prefix(model):return 'airdeliver:provider:v1:{'+hashlib.sha256(model.encode()).hexdigest()[:24]+'}'

@pytest.mark.asyncio
@pytest.mark.parametrize('axis', ['RPM','RPD','TPD','ITPM','OTPM'])
async def test_each_independent_axis_denies_before_any_other_debit(real_cache,monkeypatch,axis):
    cache,_=real_cache;model='offline-'+axis;p=prefix(model)
    amount={'RPM':1,'RPD':1,'TPD':estimated_tokens([],{})+3,'ITPM':estimated_tokens([],{}),'OTPM':3}[axis]
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(**{'PROVIDER_'+axis+'_BUDGET':amount}))
    async with shared_provider_slot(model,[],{},3,client=cache.client,limit=5000):pass
    first=await cache.client.zrange(p+':usage',0,-1)
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot(model,[],{},3,client=cache.client,limit=5000):pytest.fail('axis bypass')
    assert await cache.client.zrange(p+':usage',0,-1)==first
    assert await cache.client.zcard(p+':axis:'+axis.lower())==1
    assert not await cache.client.exists(p+':lock')

@pytest.mark.asyncio
async def test_all_axes_are_atomic_and_reconcile_only_known_usage(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-all-axes';p=prefix(model)
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPM_BUDGET=2,PROVIDER_RPD_BUDGET=2,PROVIDER_TPD_BUDGET=1000,PROVIDER_ITPM_BUDGET=500,PROVIDER_OTPM_BUDGET=40))
    async with shared_provider_slot(model,[],{},20,client=cache.client,limit=5000) as r:
        r.observe(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10,completion_tokens=5,total_tokens=15)))
    assert (await cache.client.zrange(p+':axis:itpm',0,-1))[0].endswith(':10')
    assert (await cache.client.zrange(p+':axis:otpm',0,-1))[0].endswith(':5')
    assert (await cache.client.zrange(p+':axis:tpd',0,-1))[0].endswith(':15')
    async with shared_provider_slot(model,[],{},20,client=cache.client,limit=5000):pass
    for axis in ['rpm','rpd','tpd','itpm','otpm']:
        assert await cache.client.zcard(p+':axis:'+axis)==2
    before=await cache.client.zrange(p+':usage',0,-1)
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot(model,[],{},20,client=cache.client,limit=5000):pytest.fail('atomic request bound')
    assert await cache.client.zrange(p+':usage',0,-1)==before

@pytest.mark.asyncio
async def test_observed_daily_requests_positive_count_is_decremented_and_never_raised(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-observed-requests';p=prefix(model)
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config())
    async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000) as r:
        r.headers={'x-ratelimit-remaining-requests':'1','x-ratelimit-reset-requests':'1h'}
    async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000) as r:
        r.headers={'x-ratelimit-remaining-requests':'99','x-ratelimit-reset-requests':'1h'}
    assert await cache.client.get(p+':observed_requests')=='0'
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pytest.fail('daily bound')
    assert await cache.client.pttl(p+':observed_requests')>3500000

@pytest.mark.asyncio
async def test_minute_window_expiry_does_not_reset_day_allowance(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-time-axes';p=prefix(model)
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPM_BUDGET=1,PROVIDER_RPD_BUDGET=2))
    async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pass
    now=(await cache.client.time())[0]
    minute=(await cache.client.zrange(p+':axis:rpm',0,-1))[0]
    await cache.client.zadd(p+':axis:rpm',{minute:now-61})
    async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pass
    await cache.client.zadd(p+':axis:rpm',{key:now-61 for key in await cache.client.zrange(p+':axis:rpm',0,-1)})
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pytest.fail('day reset by minute')
    assert await cache.client.zcard(p+':axis:rpd')==2

@pytest.mark.asyncio
async def test_concurrent_clients_cannot_overbook_one_request_axis(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-race';p=prefix(model)
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPM_BUDGET=3))
    accepted=[];rejected=[]
    async def call(i):
        try:
            async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):
                accepted.append(i);await asyncio.sleep(.01)
        except SharedProviderBudgetError:rejected.append(i)
    await asyncio.gather(*(call(i) for i in range(12)))
    assert len(accepted)==3 and len(rejected)==9
    assert await cache.client.zcard(p+':axis:rpm')==3
    assert await cache.client.zcard(p+':usage')==3
    assert not await cache.client.exists(p+':lock')

@pytest.mark.asyncio
async def test_configured_axis_without_redis_is_not_silently_disabled(monkeypatch):
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPD_BUDGET=5))
    with pytest.raises(SharedProviderBudgetError,match='quota_axes_require_shared_ledger'):
        async with shared_provider_slot('offline',[],{},1):pytest.fail('missing ledger')

@pytest.mark.asyncio
async def test_cancellation_keeps_unknown_axis_charge_and_releases_lock(real_cache,monkeypatch):
    cache,_=real_cache;p=prefix('offline-cancel')
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPD_BUDGET=2,PROVIDER_OTPM_BUDGET=30))
    entered=asyncio.Event()
    async def work():
        async with shared_provider_slot('offline-cancel',[],{},20,client=cache.client,limit=5000):
            entered.set();await asyncio.Event().wait()
    task=asyncio.create_task(work());await entered.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert not await cache.client.exists(p+':lock')
    assert (await cache.client.zrange(p+':axis:otpm',0,-1))[0].endswith(':20')
    assert await cache.client.zcard(p+':axis:rpd')==1

@pytest.mark.asyncio
async def test_failed_multi_axis_admission_preserves_observed_headroom(real_cache,monkeypatch):
    cache,_=real_cache;p=prefix('offline-preserve')
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_OTPM_BUDGET=1))
    await cache.client.set(p+':observed_tokens','4000',ex=60)
    await cache.client.set(p+':observed_requests','4',ex=3600)
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot('offline-preserve',[],{},2,client=cache.client,limit=5000):pytest.fail('output bound')
    assert await cache.client.get(p+':observed_tokens')=='4000'
    assert await cache.client.get(p+':observed_requests')=='4'
    assert not await cache.client.exists(p+':usage')

@pytest.mark.parametrize('value',[0,-1,True,1.5,10**10])
def test_invalid_axis_configuration_fails_closed(value):
    from app.services.provider_capacity.provider_quota_axes import axis_arguments
    with pytest.raises(SharedProviderBudgetError,match='invalid_quota_axis'):
        axis_arguments(config(PROVIDER_RPM_BUDGET=value),1,1)

@pytest.mark.asyncio
async def test_large_expired_daily_backlog_is_bounded_and_fail_closed(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-backlog';p=prefix(model);key=p+':axis:rpd'
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPD_BUDGET=300))
    now=(await cache.client.time())[0]
    await cache.client.zadd(key,{f'old-{i}:1':now-86401 for i in range(300)})
    await cache.client.set(key+':total','300',ex=86500)
    for expected in [172,44]:
        with pytest.raises(SharedProviderBudgetError):
            async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pytest.fail('backlog unresolved')
        assert await cache.client.zcard(key)==expected
        assert not await cache.client.exists(p+':lock')
        assert not await cache.client.exists(p+':usage')
    async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pass
    assert await cache.client.get(key+':total')=='1'
    assert await cache.client.zcard(key)==1
    assert await cache.client.ttl(key+':total')>86400

@pytest.mark.asyncio
async def test_reconciliation_keeps_positive_sum_ttl_and_out_of_order_successes(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-sums';p=prefix(model)
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_TPD_BUDGET=1000))
    for actual in [6,None,10]:
        async with shared_provider_slot(model,[],{},10,client=cache.client,limit=5000) as r:
            if actual is not None:r.observe(SimpleNamespace(usage=SimpleNamespace(total_tokens=actual)))
    expected=6+estimated_tokens([],{})+10+10
    assert int(await cache.client.get(p+':axis:tpd:total'))==expected
    assert await cache.client.ttl(p+':axis:tpd:total')>86400


@pytest.mark.asyncio
async def test_evicted_accumulator_cannot_grant_fresh_allowance(real_cache,monkeypatch):
    cache,_=real_cache;model='offline-eviction';p=prefix(model)
    monkeypatch.setattr('app.core.config.get_core_settings',lambda:config(PROVIDER_RPD_BUDGET=2))
    async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pass
    await cache.client.delete(p+':axis:rpd:total')
    with pytest.raises(SharedProviderBudgetError):
        async with shared_provider_slot(model,[],{},1,client=cache.client,limit=5000):pytest.fail('eviction bypass')
    assert await cache.client.zcard(p+':axis:rpd')==1
