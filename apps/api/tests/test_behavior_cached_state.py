"""Actual Redis cached inference must match artifact, dimensions and lifetime."""
import json,time
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_behavior_engine import BehaviorEngine
from tests.test_cart_persistence_outcomes import real_cache


def engine_for(cache):
    engine=object.__new__(BehaviorEngine)
    engine.brain=object();engine.cache=cache
    engine._model_namespace='test-artifact'
    engine._trained_dims={4};engine.net_config=SimpleNamespace(internal_dim=4)
    return engine


def valid_state():
    return {'model_id':'test-artifact','src_dim':4,'ts':time.time(),'pos':[1.,0.,0.,0.],'neg':[0.,1.,0.,0.]}

@pytest.mark.asyncio
@pytest.mark.parametrize('field,value',[
 ('model_id','another-artifact'),('src_dim',True),('src_dim','4'),('src_dim',8),
 ('ts',True),('ts','123'),('ts',0),('ts',float('nan')),('ts',float('inf')),
 ('ts',1),('ts',99999999999),('pos',None),('pos',[]),('pos',[1.,0.]),
 ('pos',[True,0.,0.,0.]),('pos',['1',0.,0.,0.]),('pos',[float('nan'),0.,0.,0.]),
 ('pos',[float('inf'),0.,0.,0.]),('pos',[1e308,0.,0.,0.]),('pos',[0.,0.,0.,0.]),('neg',[1.]),
])
async def test_invalid_cached_state_is_not_a_profile_or_ranking_input(real_cache,field,value):
    cache,_=real_cache;engine=engine_for(cache)
    data=valid_state();data[field]=value
    await cache.set(engine.ghost_key(7),json.dumps(data),ttl=3600)
    assert await engine.get_ghost_profile(7) is None
    products=[{'id':2},{'id':1}]
    assert await engine.collapse_wavefunction(7,products) is products
    assert products==[{'id':2},{'id':1}]

@pytest.mark.asyncio
async def test_valid_cached_state_survives_read_without_cross_owner_or_ttl_refresh(real_cache):
    cache,_=real_cache;engine=engine_for(cache);data=valid_state()
    await cache.set(engine.ghost_key(7),json.dumps(data),ttl=100)
    assert await engine.get_ghost_profile(7)==data
    assert await engine.get_ghost_profile(8) is None
    assert 0<await cache.client.ttl(engine.ghost_key(7))<=100

@pytest.mark.asyncio
@pytest.mark.parametrize('owner',[True,0,-1,'7',7.0,2147483648])
async def test_bad_owner_rejected_before_cache_read(owner):
    cache=SimpleNamespace(get=AsyncMock())
    assert await engine_for(cache).get_ghost_profile(owner) is None
    cache.get.assert_not_awaited()
