"""Small raw-state adapter for existing unit doubles; real Redis tested separately."""
import json
class SnapshotRedisAdapter:
 def __init__(self,store):self.store=store
 async def get(self,key):return json.dumps(self.store[key],separators=(',',':')) if key in self.store else None
 async def exists(self,key):return key in self.store
 async def eval(self,script,numkeys,key,owner,generation,kind,expected,value,ttl):
  if generation and (owner+':reset_pending' in self.store or str(self.store.get(owner,'0'))!=generation):return 'reset'
  current=await self.get(key)
  if (kind=='missing' and current is not None) or (kind!='missing' and current!=expected):return 'stale'
  self.store[key]=json.loads(value);return 'committed'
 def scan_iter(self,*args,**kwargs):raise NotImplementedError
