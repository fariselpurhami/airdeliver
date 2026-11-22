"""Readiness contracts with real encoder calls/timing and loopback HTTP."""
import asyncio
import json
import socket
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import numpy as np
import pytest
import uvicorn
from fastapi import FastAPI

from app.services.embedding_warmup import warm_text_encoder, WarmupPolicy, TextEmbeddingWarmupError
from app.services import ai_commerce_engine as commerce


class TimedEncoder:
    def __init__(self, durations, clock):
        self.durations = iter(durations)
        self.clock = clock
        self.calls = []
    def encode(self, text, **kwargs):
        self.calls.append((text, kwargs))
        self.clock[0] += next(self.durations)
        return np.ones(1536)


def test_real_observed_cold_pattern_requires_two_fast_samples():
    clock = [0.0]
    model = TimedEncoder([74.514, 11.493, .707, .8], clock)
    report = warm_text_encoder(model, 1536, clock=lambda: clock[0])
    assert report['state'] == 'ready' and len(model.calls) == 4
    assert report['sample_seconds'] == [74.514, 11.493, .707, .8]
    assert all(kwargs == {'convert_to_numpy': True} for _, kwargs in model.calls)
    assert commerce.EngineLimits().embedding_timeout_seconds == 25


@pytest.mark.parametrize('durations,policy', [
    ([6]*8, WarmupPolicy()),
    ([241], WarmupPolicy()),
    ([1,6,1,6], WarmupPolicy(max_attempts=4)),
])
def test_slow_or_unstable_warmup_cannot_pass(durations, policy):
    clock = [0.0]
    with pytest.raises(TextEmbeddingWarmupError):
        warm_text_encoder(TimedEncoder(durations, clock),1536,policy=policy,clock=lambda:clock[0])


@pytest.mark.parametrize('vector', [np.zeros(1536),np.ones(384),np.full(1536,np.nan)])
def test_invalid_vectors_fail_readiness(vector):
    with pytest.raises(TextEmbeddingWarmupError):
        warm_text_encoder(SimpleNamespace(encode=lambda *a,**k:vector),1536)


@pytest.mark.asyncio
async def test_startup_wait_deadline_does_not_publish_or_cancel_native_thread(monkeypatch):
    started, release, completed = threading.Event(), threading.Event(), threading.Event()
    def load():
        started.set()
        release.wait(2)
        completed.set()
        return object()
    monkeypatch.setattr(commerce,'model_registry',SimpleNamespace(reject_text_startup=lambda:None))
    monkeypatch.setattr(commerce,'get_embedding_model',load)
    monkeypatch.setattr(commerce,'STARTUP_MODEL_BUDGET_SECONDS',.03)
    try:
        with pytest.raises(TextEmbeddingWarmupError,match='deadline'):
            await commerce.initialize_query_embeddings()
        assert started.is_set() and not completed.is_set()
    finally:
        release.set()
        await asyncio.to_thread(completed.wait,1)


@pytest.mark.asyncio
async def test_actual_http_server_cannot_accept_health_until_api_lifespan_warmup(monkeypatch):
    import app.main as main
    gate=asyncio.Event()
    entered=asyncio.Event()
    async def warmup():
        entered.set()
        await gate.wait()
    monkeypatch.setattr(main,'startup_resources',AsyncMock(return_value=object()))
    monkeypatch.setattr(main,'shutdown_resources',AsyncMock())
    monkeypatch.setattr(main,'initialize_query_embeddings',warmup)
    app=FastAPI(lifespan=main.lifespan)
    @app.get('/health')
    async def health():return {'ready':True}
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    task=asyncio.create_task(server.serve(sockets=[sock]))
    try:
        await asyncio.wait_for(entered.wait(),1)
        assert not server.started
        async with httpx.AsyncClient(timeout=.15) as client:
            with pytest.raises(httpx.TransportError):
                await client.get(f'http://127.0.0.1:{port}/health')
            gate.set()
            async with asyncio.timeout(2):
                while not server.started:await asyncio.sleep(.01)
            assert (await client.get(f'http://127.0.0.1:{port}/health')).json()=={'ready':True}
    finally:
        gate.set();server.should_exit=True
        await asyncio.wait_for(task,3)
        sock.close()


@pytest.mark.asyncio
async def test_worker_health_and_readiness_reject_cold_model():
    import worker_entrypoint as worker
    runtime=worker.WorkerRuntime()
    s=runtime.services
    s.rabbitmq=SimpleNamespace(is_closed=False);s.db_engine=object()
    s.infrastructure_ready=s.consumer_ready=s.payment_ready=True
    s.refresh_readiness()
    assert not s.readiness_event.is_set()
    assert (await runtime.health_check_handler(None)).status==503
    s.ai_ready=True;s.refresh_readiness()
    assert s.readiness_event.is_set()
    assert (await runtime.health_check_handler(None)).status==200


@pytest.mark.asyncio
async def test_api_health_rejects_registry_failure(monkeypatch):
    from fastapi import Response
    from app.api.v1.endpoints import health
    monkeypatch.setattr(health,'model_registry',SimpleNamespace(text_readiness=lambda:{'state':'failed'}))
    response=Response()
    payload=await health.health_check(response,SimpleNamespace(USE_REDIS=False),SimpleNamespace(execute=AsyncMock()),None)
    assert response.status_code==503 and payload['text_embeddings']=='failed'


def test_registry_does_not_publish_failed_model_and_retries_cleanly(monkeypatch):
    registry=object.__new__(commerce.ModelRegistry)
    registry._text_model=None;registry._model_lock=threading.RLock()
    registry._text_startup_rejected=threading.Event()
    registry._device='cpu';registry._dtype='float32'
    registry._text_warmup_status={'state':'not_started'}
    model=SimpleNamespace(to=lambda *_:None,eval=lambda:None)
    monkeypatch.setattr(commerce,'SentenceTransformer',lambda *a,**k:model)
    def fail(*a,**k):raise TextEmbeddingWarmupError('unstable')
    monkeypatch.setattr(commerce,'warm_text_encoder',fail)
    with pytest.raises(TextEmbeddingWarmupError):registry.get_text_model()
    assert registry._text_model is None and registry.text_readiness()['state']=='failed'
    monkeypatch.setattr(commerce,'warm_text_encoder',lambda *a,**k:{'state':'ready','sample_seconds':[.1,.2]})
    assert registry.get_text_model() is model
    assert registry.text_readiness()['state']=='ready' and model.max_seq_length==8192


@pytest.mark.asyncio
async def test_api_startup_warmup_failure_never_yields_and_closes_resources(monkeypatch):
    import app.main as main
    resources=object()
    monkeypatch.setattr(main,'startup_resources',AsyncMock(return_value=resources))
    shutdown=AsyncMock();monkeypatch.setattr(main,'shutdown_resources',shutdown)
    monkeypatch.setattr(main,'initialize_query_embeddings',AsyncMock(side_effect=TextEmbeddingWarmupError('budget')))
    with pytest.raises(TextEmbeddingWarmupError):
        async with main.lifespan(FastAPI()):
            pytest.fail('Failed warmup cannot yield a ready application')
    shutdown.assert_awaited_once_with(resources)
