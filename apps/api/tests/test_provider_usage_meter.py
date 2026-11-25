from types import SimpleNamespace
import pytest
from app.services.provider_usage_meter import estimated_cost_nano,meter
from app.services.shared_provider_admission import Reservation
from tests.test_cart_persistence_outcomes import real_cache

def test_cost_is_estimate_with_explicit_rates_and_complete_breakdown_only():
 assert estimated_cost_nano({'prompt_tokens':1000000,'completion_tokens':1000000},150000,600000)==750000000
 assert estimated_cost_nano({'total_tokens':100},150000,600000) is None
 assert estimated_cost_nano({'prompt_tokens':1,'completion_tokens':1},None,None) is None
@pytest.mark.asyncio
async def test_real_redis_counts_unknown_separately_and_alerts_once_per_band(real_cache,monkeypatch,caplog):
 cache,_=real_cache;p='airdeliver:provider:v1:{meter-test}'
 monkeypatch.setattr('app.core.config.get_core_settings',lambda:SimpleNamespace(PROVIDER_COST_MODEL='offline',PROVIDER_INPUT_MICRO_USD_PER_MILLION=150000,PROVIDER_OUTPUT_MICRO_USD_PER_MILLION=600000))
 r=Reservation(cache.client,[p+':lock',p+':usage',p+':cooldown'],'a','a:900');r.model='offline'
 await cache.client.zadd(r.keys[1],{'a:900':1})
 await meter(r,900,1000);await meter(r,900,1000)
 keys=await cache.client.keys(p+':meter:*');row=await cache.client.hgetall(keys[0])
 assert row['calls']=='2' and row['unknown_usage_calls']=='2' and row['unknown_cost_calls']=='2'
 assert caplog.text.count('threshold_percent=80')==1
 r.observe(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100,completion_tokens=20,total_tokens=120)))
 await meter(r,900,1000)
 row=await cache.client.hgetall(keys[0]);assert row['actual_tokens']=='120' and row['estimated_cost_nano_usd']=='27000'
 assert 0<await cache.client.ttl(keys[0])<=604800
