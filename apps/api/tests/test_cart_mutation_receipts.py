"""Real Redis atomic receipt and independent service-instance replay boundary."""
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from app.services.ai_cart_service import AICartService, CartPersistenceError
from tests.test_ai_cart_service import FakeDB, make_product
from tests.test_cart_persistence_outcomes import real_cache


@pytest.mark.asyncio
async def test_committed_add_with_lost_response_replayed_by_new_service_only_once(real_cache):
    cache,_=real_cache
    payload={'user_id':1,'product_id':7,'quantity':2,'mutation_id':str(uuid4()),'notify_user':False}
    original=cache.commit_cart_mutation
    async def lost(*args,**kwargs):
        assert await original(*args,**kwargs)=='committed'
        raise ConnectionError('reply lost after transaction')
    cache.commit_cart_mutation=lost
    with pytest.raises(CartPersistenceError):
        await AICartService(FakeDB(make_product()),cache,object()).handle_add_to_cart(payload)
    cache.commit_cart_mutation=original
    db=FakeDB();db.get=AsyncMock(side_effect=AssertionError('replay must not need catalog lookup'))
    await AICartService(db,cache,object()).handle_add_to_cart(payload)
    assert (await cache.get_json_required('ai_cart:1'))['items'][0]['quantity']==2
    db.get.assert_not_awaited()
    assert 0<await cache.client.ttl(f"cart_mutation:1:{payload['mutation_id']}")<=604800


@pytest.mark.asyncio
async def test_same_id_other_payload_rejected_and_other_customer_independent(real_cache):
    cache,_=real_cache
    payload={'user_id':1,'product_id':7,'mutation_id':str(uuid4()),'notify_user':False}
    await AICartService(FakeDB(make_product()),cache,object()).handle_add_to_cart(payload)
    with pytest.raises(CartPersistenceError):
        await AICartService(FakeDB(make_product()),cache,object()).handle_add_to_cart({**payload,'quantity':2})
    await AICartService(FakeDB(make_product()),cache,object()).handle_add_to_cart({**payload,'user_id':2})
    assert (await cache.get_json_required('ai_cart:1'))['items'][0]['quantity']==1
    assert (await cache.get_json_required('ai_cart:2'))['items'][0]['quantity']==1


@pytest.mark.asyncio
async def test_atomic_competing_same_id_cart_updates_commit_once(real_cache):
    cache,_=real_cache
    receipt='cart_mutation:3:'+str(uuid4())
    results=await asyncio.gather(*(cache.commit_cart_mutation('ai_cart:3',None,{'items':[],'total':'0.00'},receipt,'same',60) for _ in range(2)))
    assert sorted(results)==['committed','replayed']
    assert await cache.commit_cart_mutation('ai_cart:3',None,{'items':[]},receipt,'different',60)=='conflict'


@pytest.mark.asyncio
async def test_remove_replay_does_not_remove_a_later_readded_product(real_cache):
    cache,_=real_cache
    add={'user_id':1,'product_id':7,'notify_user':False}
    await AICartService(FakeDB(make_product()),cache,object()).handle_add_to_cart(add)
    remove={**add,'mutation_id':str(uuid4())}
    await AICartService(FakeDB(),cache,object()).handle_remove_from_cart(remove)
    await AICartService(FakeDB(make_product()),cache,object()).handle_add_to_cart(add)
    await AICartService(FakeDB(),cache,object()).handle_remove_from_cart(remove)
    assert (await cache.get_json_required('ai_cart:1'))['items'][0]['quantity']==1
