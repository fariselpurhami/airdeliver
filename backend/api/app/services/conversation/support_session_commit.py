"""Exact snapshot CAS and owner erase fence share one Redis execution.

No long-lived lock, merge, provider retry or swallowed commit failure.
"""
import json
from uuid import uuid4
from contextvars import ContextVar
from app.services.personalization_fence import snapshot,key as owner_key

class SessionStateUnavailable(RuntimeError):pass
class SessionStateConflict(RuntimeError):pass

_snapshots=ContextVar('support_commit_snapshots',default=None)
SCRIPT="""
if ARGV[1] ~= '' then
 if redis.call('EXISTS',KEYS[2]..':reset_pending') == 1 then return 'reset' end
 if (redis.call('GET',KEYS[2]) or '0') ~= ARGV[1] then return 'reset' end
end
local current=redis.call('GET',KEYS[1])
if ARGV[2] == 'missing' then
 if current then return 'stale' end
elseif not current or current ~= ARGV[3] then return 'stale' end
redis.call('SET',KEYS[1],ARGV[4],'EX',ARGV[5])
return 'committed'
"""

async def hydrate(cache,session_id,key):
 state=_snapshots.get()
 if state is None:raise SessionStateUnavailable('No request state boundary')
 try:
  uid=int(session_id.split(':')[1]) if session_id.startswith('owner:') else None
  generation=await snapshot(cache,uid) if uid else ''
  raw=await cache.client.get(key)
  if isinstance(raw,bytes):raw=raw.decode('utf-8')
  state[key]=(raw,generation,uid)
  return None if raw is None else json.loads(raw)
 except Exception as exc:raise SessionStateUnavailable('Session state read unavailable') from exc

async def commit(cache,key,value,ttl):
 state=_snapshots.get()
 if state is None or key not in state:raise SessionStateUnavailable('Missing hydrated snapshot')
 raw,generation,uid=state[key]
 # Opaque changing revision prevents identical capped histories from ABA.
 value={**value,"_support_revision":uuid4().hex}
 try:
  result=await cache.client.eval(SCRIPT,2,key,owner_key(uid) if uid else key,generation,
   'missing' if raw is None else 'present',raw or '',json.dumps(value,separators=(',',':')),ttl)
  if isinstance(result,bytes):result=result.decode('ascii')
 except Exception as exc:raise SessionStateUnavailable('Session state commit unconfirmed') from exc
 if result!='committed':raise SessionStateConflict('Session changed or reset')
