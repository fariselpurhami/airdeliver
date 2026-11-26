"""Known cross-request lost update, retained as an explicit non-passing gap.

No provider/Redis calls. Deep-copy snapshots model separate request workers.
"""
import asyncio,json
import pytest
from app.services.neural_core_service import NeuralCoreService,RouterDecision
from app.schemas.ai_actions import NeuralCoreResponse

class SnapshotCache:
 def __init__(self):self.data={}
 async def get_json(self,key):return json.loads(json.dumps(self.data[key])) if key in self.data else None
 async def set_json(self,key,value,ttl=None):self.data[key]=json.loads(json.dumps(value))

@pytest.mark.asyncio
@pytest.mark.xfail(strict=True,reason='Known gap: simultaneous support turns overwrite the same session snapshot; distributed concurrency policy not implemented')
async def test_simultaneous_same_session_turns_preserve_both_explicit_goals():
 cache=SnapshotCache();svc=NeuralCoreService(object(),cache)
 count=0;both=asyncio.Event()
 async def route(message,memory):
  nonlocal count
  count+=1
  if count==2:both.set()
  await both.wait()
  return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 async def response(*args,**kwargs):
  return NeuralCoreResponse(text='ack',response_kind='conversation',confidence=.5,explain='controlled',telemetry={'intent':'SOCIAL_CHAT'})
 svc._analyze_intent=route;svc._shopping_response=response
 async with asyncio.timeout(2):
  await asyncio.gather(svc.handle_message(None,'first explicit goal',None,'same'),svc.handle_message(None,'second explicit goal',None,'same'))
 memory=await svc._hydrate_session('same','test')
 assert {m.content for m in memory.history if m.role=='user'}=={'first explicit goal','second explicit goal'}
