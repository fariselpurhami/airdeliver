"""Offline-only synthetic mixed-load ASGI application, never imported by production."""
import asyncio,gc,json,os,time,socket
from contextlib import asynccontextmanager
from types import SimpleNamespace
from fastapi import FastAPI,Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.limiter import build_limiter,install_rate_limiting
from app.services.free_llm_service import FreeLLMService

# The child may connect only to disposable loopback services or a Unix socket.
# This is an offline harness, not an application policy or provider fallback.
_original_connect=socket.socket.connect
def _offline_connect(sock,address):
    if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1'):
        raise RuntimeError('Offline benchmark refused non-loopback connection')
    return _original_connect(sock,address)
socket.socket.connect=_offline_connect
pauses=[];heartbeats=[];gc_start={};latencies=[]
def gc_observer(phase,info):
    key=info['generation']
    if phase=='start':gc_start[key]=time.perf_counter()
    elif key in gc_start:pauses.append({'generation':key,'seconds':time.perf_counter()-gc_start.pop(key)})

@asynccontextmanager
async def lifespan(app):
    assert gc.isenabled()
    gc.collect();gc.callbacks.append(gc_observer)
    app.state.db=create_async_engine(os.environ['TEST_POSTGRES_DSN'],pool_size=5,max_overflow=5)
    model=FreeLLMService()
    async def controlled_transport(**kwargs):
        await asyncio.sleep(.012)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer":"controlled offline completion"}'))])
    model._chat_completion=controlled_transport;app.state.model=model
    async def heartbeat():
        last=time.perf_counter()
        while True:
            await asyncio.sleep(.005);now=time.perf_counter();heartbeats.append(now-last);last=now
    pulse=asyncio.create_task(heartbeat())
    try:yield
    finally:
        pulse.cancel()
        try:await pulse
        except asyncio.CancelledError:pass
        gc.callbacks.remove(gc_observer);await app.state.db.dispose();await app.state.limiter.close()

app=FastAPI(lifespan=lifespan)
instance=build_limiter(SimpleNamespace(REDIS_URL=os.environ['BENCH_REDIS_URL'],RATE_LIMIT_DEFAULT='1000000/minute'))
install_rate_limiting(app,instance)

@app.get('/mixed')
async def mixed(request:Request,allocation:bool=False):
    began=time.perf_counter()
    async with app.state.db.connect() as db:
        result=await db.execute(text("SELECT n,md5(n::text) AS label FROM generate_series(1,100) n ORDER BY label"))
        rows=[dict(row) for row in result.mappings()]
    answer=await app.state.model.generate_response_strict('offline benchmark',json_mode=True,max_tokens=64)
    if allocation:
        # Deliberate cyclic allocation pressure. Automatic GC stays enabled;
        # no collection threshold changes, no explicit measured collections.
        for _ in range(200):
            item={'rows':rows.copy()};item['cycle']=item
    payload={'rows':rows,'model':json.loads(answer)}
    latencies.append(time.perf_counter()-began)
    return payload

@app.get('/metrics')
@instance.exempt
async def metrics(request:Request):
    return {'gc_enabled':gc.isenabled(),'gc_thresholds':gc.get_threshold(),'gc_stats':gc.get_stats(),
            'gc_pauses':pauses,'heartbeat_seconds':heartbeats,'handler_seconds':latencies}
