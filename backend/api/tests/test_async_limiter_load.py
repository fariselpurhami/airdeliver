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
    import os,subprocess,sys,gc
    if os.environ.get('AIRDELIVER_ISOLATED_ADMISSION_BENCHMARK')!='1':
        env=dict(os.environ,AIRDELIVER_ISOLATED_ADMISSION_BENCHMARK='1')
        result=subprocess.run([sys.executable,'-m','pytest','-q',__file__+'::test_real_redis_concurrent_admission_and_event_loop_latency'],env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        return
    assert gc.isenabled()
    gc.collect()  # Before measurement only, GC stays enabled throughout.
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
        assert samples and max(samples)<.2, diagnostics
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
    import os,subprocess,sys,gc
    if os.environ.get('AIRDELIVER_ISOLATED_ADMISSION_BENCHMARK')!='1':
        env=dict(os.environ,AIRDELIVER_ISOLATED_ADMISSION_BENCHMARK='1')
        result=subprocess.run([sys.executable,'-m','pytest','-q',__file__+'::test_repeated_cold_redis_bursts_keep_exact_quota_and_one_connection'],env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        return
    assert gc.isenabled()
    gc.collect()
    url,_=redis_server
    for _ in range(5):
        instance=build_limiter(settings(url,'100/minute'))
        client,slots,_=instance._state()
        collections=[];gc_started={}
        import gc
        def observe_gc(phase,info):
            generation=info.get('generation')
            if phase=='start':gc_started[generation]=time.perf_counter()
            elif generation in gc_started:collections.append((generation,round(time.perf_counter()-gc_started.pop(generation),4)))
        gc.callbacks.append(observe_gc)
        assert client.connection_pool.max_connections==1
        await client.flushdb()
        began=time.perf_counter()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(instance)),base_url='http://test') as c:
                results=await asyncio.gather(*(c.get('/plain') for _ in range(150)))
            print('COLD_BURST',round(time.perf_counter()-began,4),{c:[r.status_code for r in results].count(c) for c in (200,429,503)},'GC',collections)
            assert [r.status_code for r in results].count(200)==100
            assert [r.status_code for r in results].count(429)==50
            assert time.perf_counter()-began<1.0
        finally:
            gc.callbacks.remove(observe_gc)
            await instance.close()

@pytest.mark.asyncio
async def test_real_paused_redis_fails_closed_without_replaying_uncertain_increment(redis_server):
    from redis.asyncio import Redis
    url,_=redis_server;instance=build_limiter(settings(url,'100/minute'))
    inspector=Redis.from_url(url,socket_timeout=2)
    try:
        assert await inspector.ping()
        await inspector.execute_command('CLIENT','PAUSE',700,'ALL')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(instance)),base_url='http://test') as client:
            began=time.perf_counter()
            pending=asyncio.create_task(client.get('/plain'))
            await asyncio.sleep(.02)
            health_started=time.perf_counter()
            assert (await client.get('/health')).status_code==200
            assert time.perf_counter()-health_started<.1
            response=await pending
            assert response.status_code==503
            assert time.perf_counter()-began<1.2
            await asyncio.sleep(.8)
            keys=await inspector.keys('airdeliver:http:v2:*')
            assert len(keys)<=1
            before=int(await inspector.get(keys[0])) if keys else 0
            assert before<=1  # An uncertain increment is never retried.
            assert (await client.get('/plain')).status_code==200
            keys=await inspector.keys('airdeliver:http:v2:*')
            assert len(keys)==1 and int(await inspector.get(keys[0]))==before+1
    finally:
        await instance.close();await inspector.aclose()

@pytest.mark.asyncio
async def test_process_gc_pause_characterization_fails_closed_without_increment_replay(redis_server):
    import gc
    from redis.asyncio import Redis
    assert gc.isenabled()
    url,_=redis_server;instance=build_limiter(settings(url,'100/minute'))
    inspector=Redis.from_url(url,socket_timeout=2)
    try:
        await inspector.execute_command('CLIENT','PAUSE',900,'ALL')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(instance)),base_url='http://test') as client:
            began=time.perf_counter();pending=asyncio.create_task(client.get('/plain'))
            await asyncio.sleep(.02)
            # Deliberate stop-the-world characterization, not a latency benchmark.
            gc.collect();time.sleep(.65)
            response=await pending
            assert response.status_code==503
            assert time.perf_counter()-began<1.5
            await asyncio.sleep(.8)
            keys=await inspector.keys('airdeliver:http:v2:*')
            before=int(await inspector.get(keys[0])) if keys else 0
            assert len(keys)<=1 and before<=1
            assert (await client.get('/plain')).status_code==200
            keys=await inspector.keys('airdeliver:http:v2:*')
            assert len(keys)==1 and int(await inspector.get(keys[0]))==before+1
            assert gc.isenabled()
    finally:
        await instance.close();await inspector.aclose()
