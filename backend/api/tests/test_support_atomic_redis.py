"""Temporary real Redis support state boundaries. Synthetic adapters, no providers."""
import asyncio,hashlib
from types import SimpleNamespace
import pytest
from app.services.neural_core_service import NeuralCoreService,RouterDecision
from app.schemas.ai_actions import NeuralCoreResponse
from tests.test_cart_persistence_outcomes import real_cache

def service(cache):
 svc=NeuralCoreService(object(),cache)
 async def route(*args):return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 async def respond(*args,**kwargs):return NeuralCoreResponse(text='controlled answer',response_kind='conversation',confidence=.5,explain='synthetic',telemetry={'intent':'SOCIAL_CHAT'})
 svc._analyze_intent=route;svc._shopping_response=respond
 return svc

@pytest.mark.asyncio
@pytest.mark.parametrize('authenticated',[False,True])
async def test_two_service_instances_never_publish_two_inconsistent_snapshot_replies(real_cache,authenticated):
 cache,_=real_cache
 first,second=service(cache),service(cache);arrived=0;both=asyncio.Event()
 async def route(*args):
  nonlocal arrived
  arrived+=1
  if arrived==2:both.set()
  await both.wait()
  return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 first._analyze_intent=route;second._analyze_intent=route
 user=SimpleNamespace(id=7,full_name='Synthetic') if authenticated else None
 async with asyncio.timeout(3):
  replies=await asyncio.gather(first.handle_message(None,'first goal',user,'same-session'),second.handle_message(None,'second goal',user,'same-session'))
 assert sorted(r.response_kind for r in replies)==['conversation','system_notice']
 key='owner:7:'+hashlib.sha256(b'same-session').hexdigest() if authenticated else 'same-session'
 saved=await cache.get_json_required(first._get_session_key(key))
 assert len(saved['history'])==2
 assert 0<await cache.client.ttl(first._get_session_key(key))<=3600*24

@pytest.mark.asyncio
async def test_required_cache_read_outage_never_calls_model(real_cache):
 cache,_=real_cache;svc=service(cache);calls=[]
 async def fail(*args):raise ConnectionError('controlled read outage')
 async def route(*args):calls.append(True);return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 cache.client.get=fail;svc._analyze_intent=route
 result=await svc.handle_message(None,'synthetic goal',None,'same-session')
 assert result.response_kind=='system_notice' and calls==[]

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['write_outage','reset_before_commit','pending_reset','cancel','expired_snapshot','corrupt_snapshot'])
async def test_session_state_terminal_boundaries(real_cache,mode):
 cache,_=real_cache;svc=service(cache)
 user=SimpleNamespace(id=7,full_name='Synthetic')
 key=svc._get_session_key('owner:7:'+hashlib.sha256(b'same-session').hexdigest())
 from app.services.personalization_fence import key as generation_key
 async def route(*args):
  if mode=='write_outage':
   async def fail(*a,**k):raise ConnectionError('controlled unconfirmed commit')
   cache.client.eval=fail
  if mode=='reset_before_commit':await cache.client.incr(generation_key(7))
  if mode=='pending_reset':await cache.client.set(generation_key(7)+':reset_pending','1')
  if mode=='cancel':raise asyncio.CancelledError()
  if mode=='expired_snapshot':await cache.client.delete(key)
  return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 svc._analyze_intent=route
 if mode=='expired_snapshot':
  await cache.set_json_required(key,{'user_name':'Synthetic','history':[]},ttl=60)
 if mode=='corrupt_snapshot':await cache.client.set(key,'corrupt')
 if mode=='cancel':
  with pytest.raises(asyncio.CancelledError):await svc.handle_message(None,'goal',user,'same-session')
 else:
  reply=await svc.handle_message(None,'goal',user,'same-session')
  assert reply.response_kind=='system_notice'
 if mode not in {'expired_snapshot','corrupt_snapshot'}:assert await cache.client.get(key) is None

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['concurrent','outage','reset','cancel','followup','owner_isolation'])
async def test_mounted_http_returns_only_committed_current_turns(real_cache,mode):
 from fastapi import FastAPI
 from httpx import AsyncClient,ASGITransport
 from app.api.v1.endpoints import ai_support
 from app.api import deps
 from app.db.session import get_async_session
 from app.services.neural_core_service import get_neural_core_service
 from app.services.cache_service import get_cache_from_request
 cache,_=real_cache;app=FastAPI();app.include_router(ai_support.router,prefix='/support')
 app.dependency_overrides[get_async_session]=lambda:None
 app.dependency_overrides[get_cache_from_request]=lambda:cache
 app.dependency_overrides[deps.get_optional_current_user]=lambda:SimpleNamespace(id=7,full_name='Synthetic')
 instances=[];count=0;both=asyncio.Event();entered=asyncio.Event();seen=[]
 def create_service():
  svc=service(cache);instances.append(svc)
  async def route(message,memory):
   nonlocal count
   seen.append([turn.content for turn in memory.history if turn.role=='user'])
   if mode=='concurrent':
    count+=1
    if count==2:both.set()
    await both.wait()
   if mode=='reset':
    from app.services.personalization_fence import key
    await cache.client.incr(key(7))
   if mode=='cancel':entered.set();await asyncio.Event().wait()
   if mode=='outage':
    async def fail(*a,**k):raise ConnectionError('controlled HTTP commit outage')
    cache.client.eval=fail
   return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
  svc._analyze_intent=route;return svc
 app.dependency_overrides[get_neural_core_service]=create_service
 async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
  async def post(text):return await client.post('/support/chat',json={'message':text,'session_id':'http-synthetic'})
  if mode=='concurrent':
   replies=await asyncio.gather(post('first goal'),post('second goal'))
   assert all(r.status_code==200 for r in replies)
   assert sorted(r.json()['response_kind'] for r in replies)==['conversation','system_notice']
   assert len(instances)==2
  elif mode=='cancel':
   task=asyncio.create_task(post('cancelled goal'));await asyncio.wait_for(entered.wait(),1);task.cancel()
   with pytest.raises(asyncio.CancelledError):await task
   assert not await cache.client.keys('ai_session_v9:*')
  elif mode in {'followup','owner_isolation'}:
   assert (await post('first goal')).json()['response_kind']=='conversation'
   if mode=='owner_isolation':app.dependency_overrides[deps.get_optional_current_user]=lambda:SimpleNamespace(id=8,full_name='Other')
   assert (await post('second goal')).json()['response_kind']=='conversation'
   assert seen==[[],['first goal']] if mode=='followup' else seen==[[],[]]
  else:
   reply=await post('goal')
   assert reply.status_code==200 and reply.json()['response_kind']=='system_notice'
   assert not await cache.client.keys('ai_session_v9:*')

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['lost_commit_response','cancel_after_commit'])
async def test_commit_response_uncertainty_never_replays_or_returns_ordinary_reply(real_cache,mode):
 cache,_=real_cache;svc=service(cache);original=cache.client.eval;commits=[]
 async def uncertain(script,*args,**kwargs):
  result=await original(script,*args,**kwargs)
  if "return 'committed'" in script:
   commits.append(result)
   if mode=='cancel_after_commit':raise asyncio.CancelledError()
   raise ConnectionError('controlled reply loss after commit')
  return result
 cache.client.eval=uncertain
 if mode=='cancel_after_commit':
  with pytest.raises(asyncio.CancelledError):await svc.handle_message(None,'synthetic goal',None,'same-session')
 else:
  reply=await svc.handle_message(None,'synthetic goal',None,'same-session')
  assert reply.response_kind=='system_notice'
 assert len(commits)==1
 saved=await cache.get_json_required(svc._get_session_key('same-session'))
 assert len(saved['history'])==2

@pytest.mark.asyncio
async def test_atomic_script_rejects_reset_started_between_publication_precheck_and_commit(real_cache,monkeypatch):
 cache,_=real_cache;svc=service(cache)
 import app.services.personalization_fence as fence
 async def race(*args):
  await cache.client.incr(fence.key(7));return True
 monkeypatch.setattr(fence,'can_publish',race)
 reply=await svc.handle_message(None,'synthetic goal',SimpleNamespace(id=7,full_name='Synthetic'),'same-session')
 assert reply.response_kind=='system_notice'
 assert not await cache.client.keys('ai_session_v9:*')

@pytest.mark.asyncio
async def test_sequential_same_input_is_two_turns_not_automatic_deduplication(real_cache):
 cache,_=real_cache;svc=service(cache)
 for _ in range(2):assert (await svc.handle_message(None,'same explicit goal',None,'same-session')).response_kind=='conversation'
 saved=await cache.get_json_required(svc._get_session_key('same-session'))
 assert len(saved['history'])==4

@pytest.mark.asyncio
async def test_identical_capped_history_still_has_unique_commit_revision(real_cache):
 cache,_=real_cache;svc=service(cache)
 for _ in range(6):await svc.handle_message(None,'identical goal',None,'same-session')
 before=await cache.client.get(svc._get_session_key('same-session'))
 assert (await svc.handle_message(None,'identical goal',None,'same-session')).response_kind=='conversation'
 after=await cache.client.get(svc._get_session_key('same-session'))
 # Same capped semantic history must not make a new commit equal an old raw
 # snapshot, otherwise two concurrent identical turns can both pass CAS.
 assert before!=after

@pytest.mark.asyncio
async def test_concurrent_identical_turns_on_saturated_history_still_have_one_winner(real_cache):
 cache,_=real_cache
 seed=service(cache)
 for _ in range(6):await seed.handle_message(None,'identical goal',None,'same-session')
 services=[service(cache),service(cache)];both=asyncio.Event();count=0
 async def route(*args):
  nonlocal count
  count+=1
  if count==2:both.set()
  await both.wait()
  return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 for svc in services:svc._analyze_intent=route
 replies=await asyncio.gather(*(svc.handle_message(None,'identical goal',None,'same-session') for svc in services))
 assert sorted(r.response_kind for r in replies)==['conversation','system_notice']

@pytest.mark.asyncio
async def test_invalid_typed_snapshot_is_not_silently_fresh_context(real_cache):
 cache,_=real_cache;svc=service(cache);calls=[]
 await cache.set_json_required(svc._get_session_key('same-session'),{'user_name':'Synthetic','history':[{'role':'system','content':'invalid stored role'}]},ttl=60)
 async def route(*args):calls.append(True);return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
 svc._analyze_intent=route
 result=await svc.handle_message(None,'new question',None,'same-session')
 assert result.response_kind=='system_notice' and calls==[]

@pytest.mark.asyncio
async def test_owner_reset_immediately_after_commit_is_rechecked_before_return(real_cache):
 cache,_=real_cache;svc=service(cache);original=cache.client.eval
 from app.services.personalization_fence import key
 async def reset_after_commit(script,*args,**kwargs):
  result=await original(script,*args,**kwargs)
  if "return 'committed'" in script:await cache.client.incr(key(7))
  return result
 cache.client.eval=reset_after_commit
 reply=await svc.handle_message(None,'synthetic goal',SimpleNamespace(id=7,full_name='Synthetic'),'same-session')
 assert reply.response_kind=='system_notice'
