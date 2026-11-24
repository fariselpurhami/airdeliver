"""Single active opening per user across API/worker, no retry window or cache."""
import asyncio
import uuid
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary

_local=WeakKeyDictionary()
RELEASE="if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end;return 0"

@asynccontextmanager
async def opening_generation(cache,user_id,timeout):
    client=getattr(cache,'client',None)
    key=f'airdeliver:opening:active:v1:{user_id}'
    owner=uuid.uuid4().hex
    local=None
    if client is not None:
        # Longer than the caller's bounded generation. Process death cannot
        # retain a permanent lock. Configured-cache failures do not bypass it.
        acquired=bool(await client.set(key,owner,nx=True,px=int((timeout+5)*1000)))
    else:
        local=_local.setdefault(asyncio.get_running_loop(),set())
        acquired=user_id not in local
        if acquired:local.add(user_id)
    try:
        yield acquired
    finally:
        if acquired:
            if client is not None:await asyncio.shield(client.eval(RELEASE,1,key,owner))
            else:local.discard(user_id)
