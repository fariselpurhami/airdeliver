"""Shared rolling provider admission. Estimates are not tokenizer measurements.

Redis is authoritative across API/worker. Missing Redis config uses existing
process-local serialization only; configured-but-unreachable Redis fails closed.
Reservations survive failed/unknown requests. Successful usage reconciles them.
No prompts, generated text, credentials or customer identifiers enter Redis.
"""
import asyncio
import hashlib
import logging
import math
import uuid
from contextlib import asynccontextmanager

from contextvars import ContextVar
from dataclasses import dataclass

@dataclass
class TurnBudget:
    calls:int=0
    reserved:int=0
    def take(self,amount):
        if self.calls>=6 or self.reserved+amount>16000:
            raise SharedProviderBudgetError('turn_budget_exhausted')
        self.calls+=1;self.reserved+=amount

_turn_budget=ContextVar('provider_turn_budget',default=None)
_principal=ContextVar('provider_principal',default=None)

@asynccontextmanager
async def provider_turn_budget():
    token=_turn_budget.set(TurnBudget())
    try:yield _turn_budget.get()
    finally:_turn_budget.reset(token)

RESERVE = """
local now=tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE',KEYS[2],'-inf',now-60)
if redis.call('EXISTS',KEYS[3])==1 then return -2 end
if redis.call('EXISTS',KEYS[1])==1 then return 0 end
local total=0
for _,v in ipairs(redis.call('ZRANGE',KEYS[2],0,-1)) do total=total+tonumber(string.match(v,':(%d+)$')) end
if total+tonumber(ARGV[3])>tonumber(ARGV[4]) then return -1 end
redis.call('SET',KEYS[1],ARGV[1],'PX',ARGV[5])
redis.call('ZADD',KEYS[2],now,ARGV[2]);redis.call('EXPIRE',KEYS[2],120)
return 1
"""
FINISH = """
if ARGV[3]~='' then
 local score=redis.call('ZSCORE',KEYS[2],ARGV[2])
 if score then redis.call('ZREM',KEYS[2],ARGV[2]);redis.call('ZADD',KEYS[2],score,ARGV[3]) end
end
if redis.call('GET',KEYS[1])==ARGV[1] then redis.call('DEL',KEYS[1]) end
return 1
"""
COOLDOWN="""local old=redis.call('PTTL',KEYS[1]);if old<tonumber(ARGV[1]) then redis.call('SET',KEYS[1],'1','PX',ARGV[1]) end;return 1"""

logger=logging.getLogger("airdeliver.provider_budget")

class SharedProviderBudgetError(RuntimeError):
    pass

def estimated_tokens(messages,response_format=None):
    # Deliberately labelled estimate. Provider tokenizer/framing can differ.
    import json
    raw=json.dumps({'messages':messages,'response_format':response_format},ensure_ascii=False,separators=(',',':'))
    ascii_bytes=sum(ord(c)<128 for c in raw)
    non_ascii_bytes=sum(len(c.encode('utf-8')) for c in raw if ord(c)>=128)
    return math.ceil(ascii_bytes/3)+non_ascii_bytes+128

class Reservation:
    def __init__(self,client,keys,owner,member):
        self.client=client;self.keys=keys;self.owner=owner;self.member=member;self.actual=None
    def observe(self,response):
        value=getattr(getattr(response,'usage',None),'total_tokens',None)
        if type(value) is int and value>=0:self.actual=value
    async def quota(self,delay):
        if self.client:
            await self.client.eval(COOLDOWN,1,self.keys[2],max(1,math.ceil(delay*1000)))

@asynccontextmanager
async def _shared_provider_slot(model,messages,response_format,output,timeout=30,*,client=None,limit=None):
    from app.core.config import get_core_settings
    settings=get_core_settings()
    limit=limit or settings.PROVIDER_TPM_BUDGET
    uri=settings.REDIS_URL
    amount=estimated_tokens(messages,response_format)+output
    turn=_turn_budget.get()
    if turn is not None:turn.take(amount)
    owns_client=False
    if client is None and uri:
        from redis.asyncio import Redis
        from redis.asyncio.retry import Retry
        from redis.backoff import NoBackoff
        client=Redis.from_url(uri,decode_responses=True,socket_timeout=.5,socket_connect_timeout=.5,retry=Retry(NoBackoff(),0))
        owns_client=True
    reservation=Reservation(None,[],None,None)
    if client is None:
        yield reservation
        return
    estimate=estimated_tokens(messages,response_format)+output
    if estimate>limit:
        if owns_client:await client.aclose()
        logger.warning('provider.input_withheld stage=shared_admission reason=single_request_reservation_exceeds_budget estimated_tokens=%d limit=%d',estimate,limit)
        raise SharedProviderBudgetError('single_request_reservation_exceeds_budget')
    prefix='airdeliver:provider:v1:{'+hashlib.sha256(model.encode()).hexdigest()[:24]+'}'
    keys=[prefix+':lock',prefix+':usage',prefix+':cooldown']
    owner=uuid.uuid4().hex;member=owner+':'+str(estimate);acquired=False
    reservation=Reservation(client,keys,owner,member)
    try:
        async with asyncio.timeout(timeout):
            while True:
                status=await client.eval(RESERVE,3,*keys,owner,member,estimate,limit,math.ceil((timeout+5)*1000))
                if status==1:acquired=True;break
                if status in {-1,-2}:
                    logger.warning('provider.input_withheld stage=shared_admission reason=rolling_budget_or_cooldown_exhausted estimated_tokens=%d limit=%d',estimate,limit)
                    raise SharedProviderBudgetError('rolling_budget_or_cooldown_exhausted')
                await asyncio.sleep(.02)
            yield reservation
    finally:
        if acquired:
            actual='' if reservation.actual is None else owner+':'+str(reservation.actual)
            # Cancellation must release the lock, but its reservation remains.
            try:
                await asyncio.shield(client.eval(FINISH,2,*keys[:2],owner,member,actual))
            finally:
                if owns_client:await client.aclose()
        elif owns_client:await client.aclose()


def budgeted_turn(function):
    """Reuse nested request budget; independent turns never share counters."""
    from functools import wraps
    @wraps(function)
    async def wrapped(*args,**kwargs):
        if _turn_budget.get() is not None:return await function(*args,**kwargs)
        # Both entrypoints bind user_id before opening any provider work.
        import inspect
        bound=inspect.signature(function).bind(*args,**kwargs)
        principal=bound.arguments.get('user_id')
        payload=bound.arguments.get('message_payload')
        if isinstance(payload,dict):principal=payload.get('user_id')
        principal_token=_principal.set(principal)
        try:
            async with provider_turn_budget():return await function(*args,**kwargs)
        finally:_principal.reset(principal_token)
    return wrapped


@asynccontextmanager
async def shared_provider_slot(model,messages,response_format,output,timeout=30,*,client=None,limit=None):
    # Admission surrounds provider calls only, never deterministic cart actions.
    from app.services.paid_turn_admission import paid_turn_slot
    async with paid_turn_slot(_principal.get() if _principal.get() is not None else 'internal-provider-work'):
        async with _shared_provider_slot(model,messages,response_format,output,timeout,client=client,limit=limit) as reservation:
            yield reservation
