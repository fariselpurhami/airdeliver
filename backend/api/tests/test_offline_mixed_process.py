"""Opt-in real Uvicorn/HTTP + disposable SQL/Redis characterization, no provider."""
import asyncio,json,os,socket,subprocess,sys,time,math
from pathlib import Path
import httpx,pytest
from tests.test_limiter_boundary import redis_server

pytestmark=pytest.mark.skipif(os.getenv('RUN_OFFLINE_PROCESS_BENCHMARK')!='1',reason='explicit offline process characterization only')
def percentile(values,p):
    ordered=sorted(values)
    return ordered[max(0,math.ceil(p*len(ordered))-1)] if ordered else None

@pytest.mark.asyncio
@pytest.mark.parametrize('allocation',[False,True])
async def test_real_process_mixed_load(redis_server,tmp_path,allocation):
    url,_=redis_server
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    env=dict(os.environ,BENCH_REDIS_URL=url,GROQ_API_KEY='',TAVILY_API_KEY='',ELEVENLABS_API_KEY='')
    log=(tmp_path/'server.log').open('w')
    child=subprocess.Popen([sys.executable,'-m','uvicorn','tests.offline_mixed_process_app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],env=env,stdout=log,stderr=log)
    samples=[];statuses={};errors={};semaphore=asyncio.Semaphore(32)
    try:
        async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}',timeout=8,limits=httpx.Limits(max_connections=40,max_keepalive_connections=40)) as client:
            async with asyncio.timeout(60):
                while True:
                    try:
                        response=await client.get('/metrics')
                        if response.status_code==200:break
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.1)
            async def one():
                async with semaphore:
                    started=time.perf_counter()
                    try:
                        response=await client.get('/mixed',params={'allocation':str(allocation).lower()})
                        statuses[str(response.status_code)]=statuses.get(str(response.status_code),0)+1
                    except httpx.HTTPError as exc:errors[type(exc).__name__]=errors.get(type(exc).__name__,0)+1
                    samples.append(time.perf_counter()-started)
            started=time.perf_counter();await asyncio.gather(*(one() for _ in range(2000)));elapsed=time.perf_counter()-started
            metrics=(await client.get('/metrics')).json()
        summary={'requests':len(samples),'concurrency':32,'allocation':allocation,'elapsed_seconds':elapsed,'rps':len(samples)/elapsed,
                 'statuses':statuses,'errors':errors,'client_seconds':{k:percentile(samples,p) for k,p in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
                 'heartbeat_seconds':{k:percentile(metrics['heartbeat_seconds'],p) for k,p in [('p99',.99),('max',1)]},
                 'gc':{'enabled':metrics['gc_enabled'],'thresholds':metrics['gc_thresholds'],'collection_count':len(metrics['gc_pauses']),
                       'pause_p99_seconds':percentile([p['seconds'] for p in metrics['gc_pauses']],.99),'pause_max_seconds':percentile([p['seconds'] for p in metrics['gc_pauses']],1)},
                 'scope':'Local loopback Redis and PG19 SQL; actual Uvicorn and strict model adapter with controlled12ms transport; no provider, weights, production app startup or remote Redis.'}
        out=Path(os.environ.get('OFFLINE_BENCH_OUTPUT','/tmp/offline-mixed-process'))
        out.mkdir(parents=True,exist_ok=True)
        (out/('allocation.json' if allocation else 'steady.json')).write_text(json.dumps({'summary':summary,'metrics':metrics},indent=2))
        print('OFFLINE_MIXED_PROCESS',json.dumps(summary,sort_keys=True))
        assert metrics['gc_enabled'] and sum(statuses.values())+sum(errors.values())==2000
        # Characterization, not a latency SLO. Failures stay in the output and
        # prevent treating a partially failed run as accepted performance.
        assert statuses=={'200':2000} and not errors,summary
    finally:
        child.terminate()
        try:await asyncio.to_thread(child.wait,10)
        except subprocess.TimeoutExpired:child.kill();await asyncio.to_thread(child.wait,3)
        log.close()
