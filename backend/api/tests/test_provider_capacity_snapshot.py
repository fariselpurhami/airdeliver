import hashlib
import pytest
from app.services.provider_capacity_snapshot import capacity_snapshot
from tests.test_cart_persistence_outcomes import real_cache

@pytest.mark.asyncio
async def test_atomic_snapshot_read_only_distinguishes_absent_from_zero(real_cache):
 cache,_=real_cache;model='openai/gpt-oss-120b';p='airdeliver:provider:v1:{'+hashlib.sha256(model.encode()).hexdigest()[:24]+'}'
 first=await capacity_snapshot(cache.client,model,225000)
 assert first['utc_day_meter'] is None and first['estimated_cost_usd'] is None and first['observed_remaining_token_clamp'] is None
 assert first['billing_reconciled'] is False
 now=first['as_of_unix'];day=now//86400
 await cache.client.zadd(p+':usage',{'old:999':now-61,'known:700':now})
 await cache.client.hset(p+f':meter:{day}',mapping={'calls':2,'actual_tokens':120,'unknown_usage_calls':1,'estimated_cost_nano_usd':27000,'unknown_cost_calls':1,'private':'not-returned'})
 await cache.client.set(p+':observed_tokens','0',ex=60)
 before=await cache.client.zrange(p+':usage',0,-1)
 result=await capacity_snapshot(cache.client,model,225000)
 assert result['rolling_reserved_or_actual_tokens']==700 and result['observed_remaining_token_clamp']==0
 assert result['estimated_cost_usd']=='0.000027' and result['utc_day_meter']['unknown_cost_calls']==1
 assert 'private' not in result['utc_day_meter']
 assert before==await cache.client.zrange(p+':usage',0,-1)
