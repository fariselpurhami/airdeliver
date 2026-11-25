"""Bounded numeric daily accounting, not provider billing or spend authority."""
import logging
import math

METER="""
local now=tonumber(redis.call('TIME')[1]);local day=math.floor(now/86400)
local key=KEYS[1]..':'..day
redis.call('HINCRBY',key,'calls',1)
redis.call('HINCRBY',key,'reserved_tokens',ARGV[1])
if ARGV[2]~='' then redis.call('HINCRBY',key,'actual_tokens',ARGV[2])
else redis.call('HINCRBY',key,'unknown_usage_calls',1) end
if ARGV[3]~='' then redis.call('HINCRBY',key,'estimated_cost_nano_usd',ARGV[3])
else redis.call('HINCRBY',key,'unknown_cost_calls',1) end
redis.call('EXPIRE',key,604800)
local total=0
for _,v in ipairs(redis.call('ZRANGE',KEYS[2],0,-1)) do total=total+tonumber(string.match(v,':(%d+)$')) end
local band=0
if total>=tonumber(ARGV[4])*.95 then band=95 elseif total>=tonumber(ARGV[4])*.80 then band=80 end
if band>0 and redis.call('SET',KEYS[3]..':'..band,'1','NX','EX',60) then return band end
return 0
"""

def estimated_cost_nano(usage,input_rate,output_rate):
    # Rates are micro-USD per million tokens. Result is integer nano-USD.
    if input_rate is None or output_rate is None:return None
    prompt=usage.get('prompt_tokens');output=usage.get('completion_tokens')
    if type(prompt) is not int or type(output) is not int:return None
    return math.ceil((prompt*input_rate+output*output_rate)/1000)

async def meter(reservation,estimate,limit):
    if reservation.client is None:return
    from app.core.config import get_core_settings
    settings=get_core_settings()
    rate_in=getattr(settings,'PROVIDER_INPUT_MICRO_USD_PER_MILLION',None)
    rate_out=getattr(settings,'PROVIDER_OUTPUT_MICRO_USD_PER_MILLION',None)
    cost=estimated_cost_nano(reservation.usage,rate_in,rate_out) if reservation.model is not None and reservation.model==getattr(settings,'PROVIDER_COST_MODEL',None) else None
    prefix=reservation.keys[0].rsplit(':',1)[0]
    band=await reservation.client.eval(METER,3,prefix+':meter',reservation.keys[1],prefix+':alert',estimate,'' if reservation.actual is None else reservation.actual,'' if cost is None else cost,limit)
    if band:
        logging.getLogger('airdeliver.provider_budget').warning('provider.capacity_alert threshold_percent=%d configured_tpm=%d',band,limit)
