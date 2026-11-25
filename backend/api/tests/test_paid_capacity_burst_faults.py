"""Bounded offline fault/burst acceptance, never a real-provider load test."""
import asyncio
from types import SimpleNamespace
import pytest
from app.services.paid_turn_admission import paid_turn_slot,PaidTurnAdmissionError
from tests.test_cart_persistence_outcomes import real_cache

PREFIX='airdeliver:paid-turn:v1:{organization}'
def config():return SimpleNamespace(PROVIDER_CAPACITY_PLAN='developer',REDIS_URL=None,PROVIDER_MAX_ACTIVE_TURNS=8,PROVIDER_MAX_QUEUED_TURNS=64,PROVIDER_TURN_QUEUE_SECONDS=2,PROVIDER_TURN_LEASE_SECONDS=15)

@pytest.mark.asyncio
async def test_128_user_burst_bounds_active_and_queued_with_typed_overload(real_cache):
 cache,_=real_cache;s=config();s.PROVIDER_TURN_QUEUE_SECONDS=8
 # Separate load client avoids the fixture's .2s socket timeout under128connections.
 from redis.asyncio import Redis
 load=Redis(host='127.0.0.1',port=cache.client.connection_pool.connection_kwargs['port'],decode_responses=True,socket_timeout=5,socket_connect_timeout=5,max_connections=160)
 release=asyncio.Event();started=asyncio.Event();active=peak=0;accepted=[];rejected=[]
 async def call(user):
  nonlocal active,peak
  try:
   async with paid_turn_slot(user,client=load,settings=s):
    active+=1;peak=max(peak,active);accepted.append(user)
    if active==8:started.set()
    await release.wait();await asyncio.sleep(.002);active-=1
  except PaidTurnAdmissionError as exc:rejected.append(str(exc))
 tasks=[asyncio.create_task(call(i)) for i in range(128)]
 try:
  await asyncio.wait_for(started.wait(),1)
  # Hold first active calls long enough for all entrants to reach admission.
  async with asyncio.timeout(5):
   while len(rejected)<56:
    failures=[type(t.exception()).__name__+':'+str(t.exception()) for t in tasks if t.done() and not t.cancelled() and t.exception()]
    assert not failures,failures
    await asyncio.sleep(.01)
  counts=await cache.client.pipeline().zcard(PREFIX+':active').zcard(PREFIX+':queue').execute()
  assert counts==[8,64]
  assert len(rejected)==56 and set(rejected)=={'queue_full'}
  release.set();await asyncio.wait_for(asyncio.gather(*tasks),3)
  assert peak==8 and len(accepted)==72
  assert await cache.client.zcard(PREFIX+':active')==0
  assert await cache.client.zcard(PREFIX+':queue')==0
 finally:
  release.set()
  for task in tasks:
   if not task.done():task.cancel()
  await asyncio.gather(*tasks,return_exceptions=True)
  await load.aclose()

@pytest.mark.asyncio
async def test_expired_crash_entries_cannot_block_new_principal(real_cache):
 cache,_=real_cache;s=config();s.PROVIDER_MAX_ACTIVE_TURNS=1
 now=(await cache.client.time())[0]*1000
 await cache.client.zadd(PREFIX+':active',{'dead-active':now-1000})
 await cache.client.zadd(PREFIX+':queue',{'dead-waiter':1})
 await cache.client.zadd(PREFIX+':expiry',{'dead-waiter':now-1000})
 async with paid_turn_slot('new',client=cache.client,settings=s):
  assert await cache.client.zcard(PREFIX+':active')==1
 assert await cache.client.zcard(PREFIX+':queue')==0

@pytest.mark.asyncio
async def test_same_user_flood_is_rejected_without_filling_queue(real_cache):
 cache,_=real_cache;s=config()
 async def duplicate():
  with pytest.raises(PaidTurnAdmissionError,match='principal_already_active'):
   async with paid_turn_slot('one-user',client=cache.client,settings=s):pytest.fail('duplicate accepted')
 async with paid_turn_slot('one-user',client=cache.client,settings=s):
  await asyncio.gather(*(duplicate() for _ in range(64)))
  assert await cache.client.zcard(PREFIX+':queue')==0
  async with paid_turn_slot('another-user',client=cache.client,settings=s):pass
 # Raw identifiers are not keys; no inference that hashes are anonymous.
 assert not any('one-user' in key for key in await cache.client.keys(PREFIX+'*'))
