import asyncio
import statistics
import time
from types import SimpleNamespace
import httpx
import pytest
from fastapi import Request
from app.core.limiter import build_limiter
from tests.test_limiter_boundary import redis_server,settings,application


@pytest.mark.asyncio
async def test_real_redis_concurrent_admission_and_event_loop_latency(redis_server):
    url,_=redis_server;instance=build_limiter(settings(url,'100/second'))
    samples=[];running=True;collections=[];gc_started={}
    import gc
    def observe_gc(phase,info):
        generation=info.get('generation')
        if phase=='start':gc_started[generation]=time.perf_counter()
        elif generation in gc_started:collections.append((generation,round(time.perf_counter()-gc_started.pop(generation),4)))
    gc.callbacks.append(observe_gc)
    async def heartbeat():
        last=time.perf_counter()
        while running:
            await asyncio.sleep(.005)
            now=time.perf_counter();samples.append(now-last);last=now
    pulse=asyncio.create_task(heartbeat());started=time.perf_counter()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(instance)),base_url='http://test') as c:
            results=await asyncio.gather(*(c.get('/plain') for _ in range(150)))
        elapsed=time.perf_counter()-started
        statuses={status:sum(r.status_code==status for r in results) for status in (200,429,503)}
        diagnostics={'statuses':statuses,'elapsed':elapsed,'gc':collections,'heartbeat':max(samples,default=0)}
        assert sum(r.status_code==200 for r in results)==100, diagnostics
        assert sum(r.status_code==429 for r in results)==50, diagnostics
        assert samples and max(samples)<.2
        print({'actual_redis_requests':150,'elapsed_seconds':round(elapsed,4),
               'heartbeat_max_gap_seconds':round(max(samples),4),'success':100,'rate_limited':50})
    finally:
        gc.callbacks.remove(observe_gc)
        running=False;await pulse;await instance.close()


@pytest.mark.asyncio
async def test_delayed_native_io_keeps_loop_responsive_and_cancels(monkeypatch,redis_server):
    url,_=redis_server;instance=build_limiter(settings(url));client,_,_=instance._state()
    cancelled=asyncio.Event()
    async def stalled(*args):
        try:await asyncio.sleep(10)
        finally:cancelled.set()
    monkeypatch.setattr(client,'eval',stalled)
    app=application(instance)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
        request=asyncio.create_task(c.get('/plain'))
        await asyncio.sleep(.02)
        began=time.perf_counter();response=await c.get('/health')
        assert response.status_code==200 and time.perf_counter()-began<.1
        request.cancel()
        with pytest.raises(asyncio.CancelledError):await request
        assert cancelled.is_set()
    await instance.close()

@pytest.mark.asyncio
async def test_repeated_cold_redis_bursts_keep_exact_quota_and_one_connection(redis_server):
    url,_=redis_server
    for _ in range(5):
        instance=build_limiter(settings(url,'100/minute'))
        client,slots,_=instance._state()
        assert client.connection_pool.max_connections==1
        await client.flushdb()
        began=time.perf_counter()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(instance)),base_url='http://test') as c:
                results=await asyncio.gather(*(c.get('/plain') for _ in range(150)))
            print('COLD_BURST',round(time.perf_counter()-began,4),{c:[r.status_code for r in results].count(c) for c in (200,429,503)})
            assert [r.status_code for r in results].count(200)==100
            assert [r.status_code for r in results].count(429)==50
            assert time.perf_counter()-began<1.0
        finally:await instance.close()
