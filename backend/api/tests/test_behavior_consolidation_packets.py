"""Actual Redis queue-drain boundary rejects corrupt identities and tensors."""
import asyncio,time
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_behavior_engine import BehaviorEngine,ACTION_MAP
from tests.test_cart_persistence_outcomes import real_cache


def engine_for(cache):
    engine=object.__new__(BehaviorEngine);engine.cache=cache
    engine.net_config=SimpleNamespace(supported_dims={'dim_4':4})
    engine.embedding_sources={'dim_4':'test-source'};engine._background_tasks=set()
    engine._learning_generation=AsyncMock(return_value=('consent','0'))
    async def commit(uid,authorized,commands):
        from app.services.personalization_fence import write
        return await write(cache,uid,commands,authorized[1])
    engine._commit_learning=commit
    engine._dream_future=AsyncMock()
    return engine


def packet():
    return dict(privacy=('consent','0'),u=7,d=4,a=ACTION_MAP['view'],v=[.1,.2,.3,.4],ts=time.time(),price=20.,item_id=11)

@pytest.mark.asyncio
@pytest.mark.parametrize('field,value',[
 ('u',True),('u','7'),('u',7.),('u',0),('u',2147483648),
 ('d',True),('d',5),('d','4'),('a',True),('a',-1),('a',100),
 ('ts',float('nan')),('ts',float('inf')),('ts',True),('ts',1),('ts',99999999999),
 ('v',[.1]),('v',[True,0.,0.,0.]),('v',['.1',0.,0.,0.]),
 ('v',[float('nan'),0.,0.,0.]),('v',[float('inf'),0.,0.,0.]),('v',[1e308,0.,0.,0.]),
 ('price',True),('price',-1),('price',float('nan')),('item_id',True),('item_id','11'),('item_id',0),
])
async def test_invalid_queue_packet_never_mutates_redis_or_starts_inference(real_cache,field,value):
    cache,_=real_cache;engine=engine_for(cache);data=packet();data[field]=value
    await engine._consolidate_memory([data])
    assert await cache.client.keys('*')==[]
    assert not engine._background_tasks
    engine._dream_future.assert_not_awaited()

@pytest.mark.asyncio
async def test_valid_packet_commits_once_and_only_valid_owner_is_inferred(real_cache):
    cache,_=real_cache;engine=engine_for(cache)
    valid=packet();invalid=dict(valid,u=True)
    await engine._consolidate_memory([None,[],invalid,valid])
    if engine._background_tasks:await asyncio.gather(*tuple(engine._background_tasks))
    engine._dream_future.assert_awaited_once_with(7)
    assert await cache.client.llen(engine.stream_key(7,4))==1
    assert await cache.client.get(engine._key_active_dim(7))=='4'
    assert await cache.client.lrange(engine._key_price_hist(7),0,-1)==['20.0']
    assert await cache.client.smembers(engine._key_seen_24h(7))=={'11'}
    assert await cache.client.ttl(engine.stream_key(7,4))>0
