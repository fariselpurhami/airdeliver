"""Owner-bound Redis generation prevents erased async state being recreated."""
from contextvars import ContextVar
from contextlib import asynccontextmanager

_turn=ContextVar('personalization_generation',default=None)

SCRIPT="""
if redis.call('EXISTS',KEYS[1]..':reset_pending')==1 then return 0 end
local generation=redis.call('GET',KEYS[1]) or '0'
if generation~=ARGV[1] then return 0 end
local commands=cjson.decode(ARGV[2])
for _,cmd in ipairs(commands) do redis.call(unpack(cmd)) end
return 1
"""

def key(uid):
    if type(uid) is not int or not 0<uid<=2147483647:raise ValueError('Invalid personalization owner')
    return f'personalization:generation:{uid}'

async def generation(cache,uid):
    if await cache.client.exists(key(uid)+':reset_pending'):raise RuntimeError('Personalization reset pending')
    value=await cache.client.get(key(uid))
    return str(value or '0')

async def snapshot(cache,uid):
    current=_turn.get()
    if current and current[0]==uid:return current[1]
    return await generation(cache,uid)

async def write(cache,uid,commands,expected=None):
    import json
    expected=await snapshot(cache,uid) if expected is None else expected
    return bool(await cache.client.eval(SCRIPT,1,key(uid),expected,json.dumps(commands)))

@asynccontextmanager
async def turn(cache,uid):
    expected=await generation(cache,uid)
    token=_turn.set((uid,expected))
    try:yield expected
    finally:_turn.reset(token)

async def unchanged(cache,uid,expected):
    return await generation(cache,uid)==expected


def guarded_turn(user_argument):
    from functools import wraps
    def decorate(function):
        @wraps(function)
        async def wrapped(self,*args,**kwargs):
            uid=user_argument(args,kwargs)
            if type(uid) is not int or uid<=0:return await function(self,*args,**kwargs)
            # Lightweight test adapters/no-state backends cannot retain data.
            try:client=self.cache.client
            except (AttributeError,RuntimeError):return await function(self,*args,**kwargs)
            if not callable(getattr(client,'eval',None)) or not callable(getattr(client,'scan_iter',None)):return await function(self,*args,**kwargs)
            async with turn(self.cache,uid):return await function(self,*args,**kwargs)
        return wrapped
    return decorate

async def can_publish(cache,uid):
    current=_turn.get()
    if current and current[0]==uid:return await unchanged(cache,uid,current[1])
    return True
