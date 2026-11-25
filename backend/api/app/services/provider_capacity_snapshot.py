"""Atomic read-only operator snapshot. No provider call or quota adjustment."""
import hashlib
from decimal import Decimal

SNAPSHOT="""
local now=tonumber(redis.call('TIME')[1]);local day=math.floor(now/86400)
local values=redis.call('ZRANGEBYSCORE',KEYS[1],now-59,'+inf')
local total=0
for _,v in ipairs(values) do total=total+tonumber(string.match(v,':(%d+)$')) end
return {now,total,redis.call('HGETALL',KEYS[2]..':'..day),redis.call('GET',KEYS[3]) or '',redis.call('PTTL',KEYS[4]),redis.call('ZCOUNT',KEYS[5],now*1000,'+inf'),redis.call('ZCARD',KEYS[6])}
"""
FIELDS={'calls','reserved_tokens','actual_tokens','unknown_usage_calls','estimated_cost_nano_usd','unknown_cost_calls'}
async def capacity_snapshot(client,model,limit):
    prefix='airdeliver:provider:v1:{'+hashlib.sha256(model.encode()).hexdigest()[:24]+'}'
    gate='airdeliver:paid-turn:v1:{organization}'
    row=await client.eval(SNAPSHOT,6,prefix+':usage',prefix+':meter',prefix+':observed_tokens',prefix+':cooldown',gate+':active',gate+':queue')
    raw=dict(zip(row[2][::2],row[2][1::2]));meter={k:int(v) for k,v in raw.items() if k in FIELDS and str(v).isdigit()}
    known='estimated_cost_nano_usd' in meter
    return {'as_of_unix':int(row[0]),'model':model,'configured_local_tpm':limit,'rolling_reserved_or_actual_tokens':int(row[1]),'observed_remaining_token_clamp':int(row[3]) if str(row[3]).isdigit() else None,'shared_cooldown_ms':max(0,int(row[4])),'active_provider_invocations':int(row[5]),'queued_entries_including_expiring':int(row[6]),'utc_day_meter':meter or None,'estimated_cost_usd':str(Decimal(meter['estimated_cost_nano_usd'])/Decimal(1000000000)) if known else None,'billing_reconciled':False,'scope':'local shared ledger only; not provider account limits, full-chain availability or billing'}
