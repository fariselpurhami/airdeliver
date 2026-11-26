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

@pytest.mark.asyncio
@pytest.mark.xfail(strict=True,reason='Known gap: failed support persistence does not change published response or signal lost continuity')
async def test_write_failure_cannot_publish_an_ordinary_reply_as_if_state_committed():
 class FailedWriteCache(SnapshotCache):
  async def set_json(self,*args,**kwargs):raise ConnectionError('controlled write outage')
 svc=NeuralCoreService(object(),FailedWriteCache())
 async def route(*args):return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 async def response(*args,**kwargs):return NeuralCoreResponse(text='ack',response_kind='conversation',confidence=.5,explain='controlled',telemetry={'intent':'SOCIAL_CHAT'})
 svc._analyze_intent=route;svc._shopping_response=response
 result=await svc.handle_message(None,'explicit goal',None,'same')
 assert result.response_kind=='system_notice'

@pytest.mark.asyncio
async def test_cancel_before_completion_does_not_commit_half_turn():
 cache=SnapshotCache();svc=NeuralCoreService(object(),cache);started=asyncio.Event()
 async def route(*args):
  started.set();await asyncio.Event().wait()
 svc._analyze_intent=route
 request=asyncio.create_task(svc.handle_message(None,'cancelled goal',None,'same'))
 await asyncio.wait_for(started.wait(),1)
 request.cancel()
 with pytest.raises(asyncio.CancelledError):await request
 assert cache.data=={}

@pytest.mark.asyncio
async def test_concurrent_distinct_sessions_keep_their_own_turns():
 cache=SnapshotCache();svc=NeuralCoreService(object(),cache);count=0;both=asyncio.Event()
 async def route(*args):
  nonlocal count
  count+=1
  if count==2:both.set()
  await both.wait()
  return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 async def response(*args,**kwargs):return NeuralCoreResponse(text='ack',response_kind='conversation',confidence=.5,explain='controlled',telemetry={'intent':'SOCIAL_CHAT'})
 svc._analyze_intent=route;svc._shopping_response=response
 async with asyncio.timeout(2):
  await asyncio.gather(svc.handle_message(None,'goal one',None,'one'),svc.handle_message(None,'goal two',None,'two'))
 for sid,wanted in [('one','goal one'),('two','goal two')]:
  memory=await svc._hydrate_session(sid,'test')
  assert [m.content for m in memory.history if m.role=='user']==[wanted]
