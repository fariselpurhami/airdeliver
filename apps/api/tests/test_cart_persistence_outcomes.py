"""Real disposable Redis transport plus cart failure-outcome contracts."""
import asyncio
import json
import os
import shutil
import socket
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from app.services.cache_service import RedisCacheClient, NoOpCacheClient
from app.services.ai_cart_service import AICartService
from tests.test_ai_cart_service import FakeDB, FakeCache, make_product


@pytest_asyncio.fixture
async def real_cache(tmp_path):
    binary=os.environ.get('TEST_REDIS_SERVER_BIN') or shutil.which('redis-server')
    if not binary:pytest.skip('Disposable Redis server binary required')
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    with (tmp_path/'server.log').open('w') as log:
        process=subprocess.Popen([binary,'--bind','127.0.0.1','--port',str(port),'--save','','--appendonly','no','--dir',str(tmp_path)],stdout=log,stderr=log)
        raw=Redis(host='127.0.0.1',port=port,decode_responses=True,socket_timeout=.2,socket_connect_timeout=.2)
        cache=RedisCacheClient(f'redis://127.0.0.1:{port}/0');cache._redis=raw
        try:
            async with asyncio.timeout(3):
                while True:
                    try:
                        if await raw.ping():break
                    except Exception:await asyncio.sleep(.02)
            yield cache,process
        finally:
            await raw.aclose()
            if process.poll() is None:
                process.terminate();await asyncio.to_thread(process.wait,3)


@pytest.mark.asyncio
async def test_real_redis_required_read_write_delete_and_corruption(real_cache):
    cache,_=real_cache
    await cache.set_json_required('cart:test',{'items':[]},ttl=60)
    assert await cache.get_json_required('cart:test')=={'items':[]}
    assert 0<await cache.client.ttl('cart:test')<=60
    await cache.client.set('cart:test','not valid json')
    with pytest.raises(Exception):await cache.get_json_required('cart:test')
    await cache.delete_required('cart:test')
    assert await cache.get_json_required('cart:test') is None


@pytest.mark.asyncio
async def test_actual_redis_disconnect_is_not_suppressed_on_required_operations(real_cache):
    cache,process=real_cache
    process.terminate();await asyncio.to_thread(process.wait,3)
    for call in [lambda:cache.get_json_required('x'),lambda:cache.set_json_required('x',{}),lambda:cache.delete_required('x')]:
        with pytest.raises(Exception):await call()


@pytest.mark.asyncio
async def test_noop_backend_cannot_claim_required_cart_persistence():
    for call in [lambda:NoOpCacheClient().get_json_required('x'),lambda:NoOpCacheClient().set_json_required('x',{}),lambda:NoOpCacheClient().delete_required('x')]:
        with pytest.raises(NotImplementedError):await call()


@pytest.mark.asyncio
async def test_cart_write_failure_never_emits_preview_success_or_confirmation():
    cache=FakeCache()
    cache.set_json_required=AsyncMock(side_effect=ConnectionError('offline'))
    svc=AICartService(FakeDB(make_product()),cache,object())
    with pytest.raises(Exception):await svc.handle_add_to_cart({'user_id':1,'product_id':7})
    assert not any(p['type'] in {'success_text','cart_preview','confirmation_prompt'} for _,p in cache.published)


@pytest.mark.asyncio
async def test_cart_read_failure_never_resets_to_empty_or_overwrites():
    cache=FakeCache()
    cache.get_json_required=AsyncMock(side_effect=ConnectionError('offline'))
    svc=AICartService(FakeDB(make_product()),cache,object())
    with pytest.raises(Exception):await svc.handle_add_to_cart({'user_id':1,'product_id':7})
    assert cache.sets==[]


@pytest.mark.asyncio
async def test_corrupt_cart_cannot_be_overwritten_by_add():
    cache=FakeCache({'items':[{'bogus':True}]})
    svc=AICartService(FakeDB(make_product()),cache,object())
    with pytest.raises(Exception):await svc.handle_add_to_cart({'user_id':1,'product_id':7})
    assert cache.sets==[]


@pytest.mark.asyncio
async def test_real_redis_cart_roundtrip_then_outage_never_reports_success(real_cache):
    from app.services.ai_cart_service import CartPersistenceError
    cache,process=real_cache
    published=[]
    async def capture(user_id,payload):published.append(payload)
    svc=AICartService(FakeDB(make_product()),cache,object());svc._send_to_ui=capture
    await svc.handle_add_to_cart({'user_id':1,'product_id':7,'quantity':2})
    assert (await cache.get_json_required('ai_cart:1'))['items'][0]['quantity']==2
    assert any(p['type']=='success_text' for p in published)
    process.terminate();await asyncio.to_thread(process.wait,3);published.clear()
    with pytest.raises(CartPersistenceError):
        await svc.handle_add_to_cart({'user_id':1,'product_id':7})
    assert published==[]


@pytest.mark.asyncio
async def test_clear_failure_does_not_emit_empty_preview():
    from app.services.ai_cart_service import CartPersistenceError
    cache=FakeCache({'items':[]});cache.delete_required=AsyncMock(side_effect=ConnectionError('offline'))
    svc=AICartService(FakeDB(),cache,object())
    with pytest.raises(CartPersistenceError):await svc.handle_clear_cart({'user_id':1})
    assert cache.published==[]


@pytest.mark.asyncio
async def test_saved_list_commit_then_cleanup_failure_never_claims_empty_cart_or_retries_database():
    cart={'items':[{'product_id':7,'name':'Shoes','quantity':1,'price':'19.99'}],'total':'19.99'}
    cache=FakeCache(cart);cache.delete_required=AsyncMock(side_effect=ConnectionError('offline'))
    db=FakeDB(make_product())
    await AICartService(db,cache,object()).handle_save_cart({'user_id':1})
    assert db.commits==1 and db.rollbacks==0
    assert cache._cart==cart
    assert not any(p['type'] in {'cart_preview','success_text'} for _,p in cache.published)
    assert any('saved list was recorded' in str(p.get('content','')) for _,p in cache.published)
    assert any('before saving again' in str(p.get('content','')) for _,p in cache.published)
