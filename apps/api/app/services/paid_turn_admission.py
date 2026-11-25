"""Bounded distributed paid-profile turn fairness, no provider calls or raw IDs.

FIFO among admitted distinct principals. Same-principal overlap is withheld so
one caller cannot occupy the queue. Deadlines and cancellation remove leases.
"""
import asyncio
import hashlib
import uuid
from contextlib import asynccontextmanager

ENTER="""
local clock=redis.call('TIME')
local now=tonumber(clock[1])*1000+math.floor(tonumber(clock[2])/1000)
local seq=redis.call('INCR',KEYS[4])
redis.call('PEXPIRE',KEYS[4],120000)
redis.call('ZREMRANGEBYSCORE',KEYS[1],'-inf',now)
redis.call('ZREMRANGEBYSCORE',KEYS[5],'-inf',now)
for _,id in ipairs(redis.call('ZRANGE',KEYS[2],0,-1)) do
 if not redis.call('ZSCORE',KEYS[5],id) then redis.call('ZREM',KEYS[2],id) end
end
if redis.call('GET',KEYS[3])~=ARGV[1] then
 if redis.call('EXISTS',KEYS[3])==1 then return -2 end
 if redis.call('ZCARD',KEYS[2])>=tonumber(ARGV[3]) then return -1 end
 redis.call('SET',KEYS[3],ARGV[1],'PX',ARGV[4])
 redis.call('ZADD',KEYS[2],seq,ARGV[1])
 redis.call('ZADD',KEYS[5],now+tonumber(ARGV[4]),ARGV[1])
end
local first=redis.call('ZRANGE',KEYS[2],0,0)[1]
if first==ARGV[1] and redis.call('ZCARD',KEYS[1])<tonumber(ARGV[2]) then
 redis.call('ZREM',KEYS[2],ARGV[1]);redis.call('ZREM',KEYS[5],ARGV[1])
 redis.call('ZADD',KEYS[1],now+tonumber(ARGV[4]),ARGV[1])
 redis.call('PEXPIRE',KEYS[1],tonumber(ARGV[4])+1000)
 return 1
end
redis.call('PEXPIRE',KEYS[2],tonumber(ARGV[4])+1000)
redis.call('PEXPIRE',KEYS[5],tonumber(ARGV[4])+1000)
return 0
"""
LEAVE="""
redis.call('ZREM',KEYS[1],ARGV[1]);redis.call('ZREM',KEYS[2],ARGV[1]);redis.call('ZREM',KEYS[5],ARGV[1])
if redis.call('GET',KEYS[3])==ARGV[1] then redis.call('DEL',KEYS[3]) end
return 1
"""
from app.services.shared_provider_admission import SharedProviderBudgetError
class PaidTurnAdmissionError(SharedProviderBudgetError):pass

@asynccontextmanager
async def paid_turn_slot(principal,*,client=None,settings=None):
    if settings is None:
        from app.core.config import get_core_settings
        settings=get_core_settings()
    if getattr(settings,'PROVIDER_CAPACITY_PLAN','free')=='free':
        yield;return
    if principal is None:raise PaidTurnAdmissionError('principal_required')
    own=False
    if client is None:
        if not settings.REDIS_URL:raise PaidTurnAdmissionError('shared_ledger_required')
        from redis.asyncio import Redis
        from redis.asyncio.retry import Retry
        from redis.backoff import NoBackoff
        client=Redis.from_url(settings.REDIS_URL,decode_responses=True,socket_timeout=.5,socket_connect_timeout=.5,retry=Retry(NoBackoff(),0));own=True
    prefix='airdeliver:paid-turn:v1:{organization}'
    # Hash is pseudonymous, not anonymous; no raw principal in Redis/logs.
    digest=hashlib.sha256(str(principal).encode()).hexdigest()
    keys=[prefix+':active',prefix+':queue',prefix+':principal:'+digest,prefix+':sequence',prefix+':expiry']
    owner=uuid.uuid4().hex
    wait=settings.PROVIDER_TURN_QUEUE_SECONDS
    lease=settings.PROVIDER_TURN_LEASE_SECONDS
    if lease<=wait:raise PaidTurnAdmissionError('invalid_turn_lease')
    try:
        try:
            async with asyncio.timeout(wait):
                while True:
                    status=await client.eval(ENTER,5,*keys,owner,settings.PROVIDER_MAX_ACTIVE_TURNS,settings.PROVIDER_MAX_QUEUED_TURNS,lease*1000)
                    if status==1:break
                    if status in {-1,-2}:raise PaidTurnAdmissionError('queue_full' if status==-1 else 'principal_already_active')
                    await asyncio.sleep(.05)
        except TimeoutError as exc:raise PaidTurnAdmissionError('queue_deadline') from exc
        # Hard lease bound prevents expired turns continuing beside new owners.
        async with asyncio.timeout(lease-wait):yield
    finally:
        try:await asyncio.shield(client.eval(LEAVE,5,*keys,owner))
        finally:
            if own:await client.aclose()
