"""Retain numeric quota headers without exposing raw response or provider text."""
import re

async def observed_create(create,reservation,**kwargs):
    # Use native raw-response API only for the real SDK, not arbitrary adapters.
    from groq.resources.chat.completions import AsyncCompletions
    resource=getattr(create,'__self__',None)
    if isinstance(resource,AsyncCompletions) and not kwargs.get('stream'):
        raw=await resource.with_raw_response.create(**kwargs)
        reservation.headers=dict(raw.headers)
        return await raw.parse()
    return await create(**kwargs)

def reset_seconds(value):
    if not isinstance(value,str) or len(value)>32:return None
    if not re.fullmatch(r'(?:\d+(?:\.\d+)?[hms])+',value):return None
    total=sum(float(n)*{'h':3600,'m':60,'s':1}[u] for n,u in re.findall(r'(\d+(?:\.\d+)?)([hms])',value))
    return min(86400,max(1,total))

def numeric_headers(headers):
    out={}
    for key in ('limit-tokens','remaining-tokens','remaining-requests'):
        value=headers.get('x-ratelimit-'+key)
        if isinstance(value,str) and re.fullmatch(r'\d{1,12}',value):out[key]=int(value)
    for unit in ('tokens','requests'):
        value=reset_seconds(headers.get('x-ratelimit-reset-'+unit))
        if value is not None:out['reset-'+unit]=value
    return out

HEADER_LIMIT="""
local old=redis.call('GET',KEYS[1])
local ttl=redis.call('PTTL',KEYS[1])
if not old then redis.call('SET',KEYS[1],ARGV[1],'PX',ARGV[2])
elseif tonumber(ARGV[1])<tonumber(old) then redis.call('SET',KEYS[1],ARGV[1],'PX',math.max(ttl,tonumber(ARGV[2]))) end
return 1
"""
async def observe_headers(reservation):
    if not reservation.client or not reservation.headers:return
    values=numeric_headers(reservation.headers)
    if 'remaining-tokens' in values:
        ttl=max(60000,int(values.get('reset-tokens',60)*1000))
        await reservation.client.eval(HEADER_LIMIT,1,reservation.keys[0].rsplit(':',1)[0]+':observed_tokens',values['remaining-tokens'],ttl)
    if values.get('remaining-requests')==0:
        # Groq request headers refer to daily requests, never reinterpret as RPM.
        await reservation.quota(values.get('reset-requests',86400))
    if values:
        import logging
        logging.getLogger('airdeliver.provider_budget').info('provider.observed_quota metadata=%s',values)
