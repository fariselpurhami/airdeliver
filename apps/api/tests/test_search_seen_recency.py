"""Actual Redis shared opening/search recency, never behavioral preferences."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from tests.test_cart_persistence_outcomes import real_cache
from app.services.ai_nlu_service import AINLUService,RedisProductFreshnessRepository,RedisKeys

@pytest.mark.asyncio
async def test_published_search_ids_share_opening_recency_and_owner_isolation(real_cache):
    cache,_=real_cache
    svc=AINLUService(object(),object(),object(),cache,SimpleNamespace(),behavior_engine=SimpleNamespace(register_interaction=AsyncMock()))
    await svc._mark_products_as_seen(41,[{'id':7},{'id':8},{'id':True},{'id':-1}])
    assert await svc.freshness_repo.get_recent_product_ids(41)=={7,8}
    assert await svc.freshness_repo.get_recent_product_ids(42)==set()
    assert await cache.client.smembers(RedisKeys.seen_products(41)) in ({'7','8'},{b'7',b'8'})
    assert await cache.client.ttl('airdeliver:freshness:41:shown_at')>0
    svc.behavior_engine.register_interaction.assert_not_awaited()

@pytest.mark.asyncio
async def test_recency_write_prunes_expired_members_and_expires_sortedset(real_cache):
    cache,_=real_cache;clock=[1000.]
    repo=RedisProductFreshnessRepository(cache,clock=lambda:clock[0])
    await repo.mark_products_as_seen(43,{7},ttl_seconds=10)
    clock[0]+=200000
    await repo.mark_products_as_seen(43,{8},ttl_seconds=10)
    assert await repo.get_recent_product_ids(43)=={8}
    members=await cache.client.zrange('airdeliver:freshness:43:shown_at',0,-1)
    assert members in (['8'],[b'8'])
    assert await cache.client.ttl('airdeliver:freshness:43:shown_at')>0

@pytest.mark.asyncio
async def test_actual_behavior_exposure_unifies_display_only_without_model_or_profile(real_cache):
    from app.services.ai_behavior_engine import BehaviorEngine
    cache,_=real_cache
    behavior=object.__new__(BehaviorEngine);behavior.cache=cache
    behavior.register_interaction=AsyncMock(side_effect=AssertionError('must not infer'))
    behavior.track_interaction=AsyncMock(side_effect=AssertionError('must not train'))
    svc=AINLUService(object(),object(),object(),cache,SimpleNamespace(),behavior_engine=behavior)
    await svc._mark_products_as_seen(44,[{'id':11}])
    assert await svc.freshness_repo.get_recent_product_ids(44)=={11}
    assert await cache.client.smembers(behavior._key_seen_24h(44)) in ({'11'},{b'11'})
    assert await cache.client.smembers(behavior._key_seen_24h(45))==set()
    behavior.register_interaction.assert_not_awaited();behavior.track_interaction.assert_not_awaited()
