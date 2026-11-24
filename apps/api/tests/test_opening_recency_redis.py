import pytest
from app.services.ai_nlu_service import RedisProductFreshnessRepository
from tests.test_cart_persistence_outcomes import real_cache


@pytest.mark.asyncio
async def test_actual_redis_cooldown_reopens_products_without_clearing_history(real_cache):
    cache,_=real_cache;clock=[1000000.]
    repo=RedisProductFreshnessRepository(cache,clock=lambda:clock[0])
    await repo.mark_products_as_seen(3,{11,12})
    assert await repo.get_recent_product_ids(3)=={11,12}
    clock[0]+=86399
    assert await repo.get_recent_product_ids(3)=={11,12}
    clock[0]+=2
    assert await repo.get_recent_product_ids(3)==set()
    assert await repo.get_seen_product_ids(3)=={11,12}
    await repo.mark_products_as_seen(3,{12})
    assert await repo.get_recent_product_ids(3)=={12}
    assert await repo.get_seen_product_ids(3)=={11,12}
    assert await repo.get_recent_product_ids(4)==set()


@pytest.mark.asyncio
async def test_legacy_seen_set_without_timestamps_does_not_permanently_hide_catalog(real_cache):
    cache,_=real_cache
    await cache.client.sadd('airdeliver:freshness:3',21,22)
    repo=RedisProductFreshnessRepository(cache)
    assert await repo.get_recent_product_ids(3)==set()
    assert await repo.get_seen_product_ids(3)=={21,22}
