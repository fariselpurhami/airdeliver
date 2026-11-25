"""Real Redis concurrent offline acceptance, no provider or paid account."""
import asyncio
from types import SimpleNamespace
import pytest
from app.services.paid_turn_admission import paid_turn_slot,PaidTurnAdmissionError
from tests.test_cart_persistence_outcomes import real_cache

def config(**kw):return SimpleNamespace(**dict(PROVIDER_CAPACITY_PLAN='developer',REDIS_URL=None,PROVIDER_MAX_ACTIVE_TURNS=2,PROVIDER_MAX_QUEUED_TURNS=8,PROVIDER_TURN_QUEUE_SECONDS=1,PROVIDER_TURN_LEASE_SECONDS=15,**kw))
@pytest.mark.asyncio
async def test_many_distinct_users_never_exceed_global_active_bound(real_cache):
 cache,_=real_cache;active=peak=0;completed=[]
 async def work(user):
  nonlocal active,peak
  async with paid_turn_slot(user,client=cache.client,settings=config()):
   active+=1;peak=max(peak,active);await asyncio.sleep(.02);completed.append(user);active-=1
 await asyncio.gather(*(work(i) for i in range(8)))
 assert peak==2 and len(completed)==8
 assert not await cache.client.zcard('airdeliver:paid-turn:v1:{organization}:active')
@pytest.mark.asyncio
async def test_same_principal_flood_cannot_take_second_slot(real_cache):
 cache,_=real_cache
 async with paid_turn_slot('private-user',client=cache.client,settings=config()):
  with pytest.raises(PaidTurnAdmissionError,match='principal_already_active'):
   async with paid_turn_slot('private-user',client=cache.client,settings=config()):pytest.fail('overlap')
  async with paid_turn_slot('different',client=cache.client,settings=config()):pass
 assert all('private-user' not in k for k in await cache.client.keys('*'))
@pytest.mark.asyncio
async def test_cancelled_waiter_removed_and_next_user_progresses(real_cache):
 cache,_=real_cache;s=config();s.PROVIDER_MAX_ACTIVE_TURNS=1
 async def waiting():
  async with paid_turn_slot('cancel',client=cache.client,settings=s):pytest.fail('must wait')
 async with paid_turn_slot('first',client=cache.client,settings=s):
  task=asyncio.create_task(waiting());await asyncio.sleep(.08);task.cancel()
  with pytest.raises(asyncio.CancelledError):await task
 async with paid_turn_slot('next',client=cache.client,settings=s):pass
 assert not await cache.client.zcard('airdeliver:paid-turn:v1:{organization}:queue')
@pytest.mark.asyncio
async def test_paid_requires_distributed_ledger_and_principal():
 with pytest.raises(PaidTurnAdmissionError,match='principal_required'):
  async with paid_turn_slot(None,settings=config()):pytest.fail('no principal')
 with pytest.raises(PaidTurnAdmissionError,match='shared_ledger_required'):
  async with paid_turn_slot(1,settings=config()):pytest.fail('no redis')
@pytest.mark.asyncio
async def test_free_guard_unchanged():
 s=config();s.PROVIDER_CAPACITY_PLAN='free'
 async with paid_turn_slot(None,settings=s):pass

@pytest.mark.asyncio
async def test_queue_bound_deadline_and_outage_fail_closed(real_cache):
 cache,process=real_cache;s=config();s.PROVIDER_MAX_ACTIVE_TURNS=1;s.PROVIDER_MAX_QUEUED_TURNS=1;s.PROVIDER_TURN_QUEUE_SECONDS=.18
 async def waiter():
  async with paid_turn_slot('waiter',client=cache.client,settings=s):pytest.fail('wait')
 async with paid_turn_slot('holder',client=cache.client,settings=s):
  task=asyncio.create_task(waiter());await asyncio.sleep(.07)
  with pytest.raises(PaidTurnAdmissionError,match='queue_full'):
   async with paid_turn_slot('overflow',client=cache.client,settings=s):pytest.fail('full')
  with pytest.raises(PaidTurnAdmissionError,match='queue_deadline'):await task
 assert not await cache.client.zcard('airdeliver:paid-turn:v1:{organization}:queue')
 process.terminate();await asyncio.to_thread(process.wait,3)
 with pytest.raises(Exception):
  async with paid_turn_slot('offline',client=cache.client,settings=s):pytest.fail('outage')

@pytest.mark.asyncio
async def test_request_identity_context_covers_both_entrypoint_shapes(monkeypatch):
 from app.services.shared_provider_admission import budgeted_turn,_principal
 seen=[]
 class Service:
  @budgeted_turn
  async def process(self,message_payload):seen.append(_principal.get())
  @budgeted_turn
  async def initial(self,user_id):seen.append(_principal.get())
 svc=Service();await svc.process({'user_id':7});await svc.initial(user_id=9)
 assert seen==[7,9] and _principal.get() is None
