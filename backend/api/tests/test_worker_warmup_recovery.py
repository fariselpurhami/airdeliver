import asyncio
import json
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock
import numpy as np
import pytest
from app.services.orchestration import worker_entrypoint as worker
from app.services import ai_commerce_engine as commerce
from app.services.embedding_warmup import WarmupPolicy,warm_text_encoder,TextEmbeddingWarmupError
from tests.test_embedding_startup_readiness import TimedEncoder
from tests.test_cart_worker_retry_boundary import message


def test_slow_cold_hardware_can_warm_with_larger_budget_without_relaxing_fast_sample_gate():
    clock=[0.]
    model=TimedEncoder([37.59]*7+[.7,.8],clock)
    with pytest.raises(TextEmbeddingWarmupError):
        warm_text_encoder(model,1536,clock=lambda:clock[0])
    clock=[0.];model=TimedEncoder([37.59]*7+[.7,.8],clock)
    report=warm_text_encoder(model,1536,policy=WarmupPolicy(budget_seconds=1200,max_attempts=32),clock=lambda:clock[0])
    assert report['state']=='ready' and len(model.calls)==9
    slow_clock=[0.]
    with pytest.raises(TextEmbeddingWarmupError):
        warm_text_encoder(TimedEncoder([37.59]*32,slow_clock),1536,
            policy=WarmupPolicy(budget_seconds=1200,max_attempts=32),clock=lambda:slow_clock[0])


@pytest.mark.asyncio
async def test_worker_recovers_failed_ai_and_health_becomes_ready(monkeypatch):
    runtime=worker.WorkerRuntime();s=runtime.services
    s.rabbitmq=SimpleNamespace(is_closed=False);s.db_engine=object()
    s.infrastructure_ready=s.consumer_ready=s.payment_ready=True;s.ai_degraded=True;s.startup_error='AI_INIT_DEGRADED'
    monkeypatch.setattr(worker,'get_core_settings',lambda:SimpleNamespace(AI_RECOVERY_INTERVAL_SECONDS=.01))
    attempts=[]
    async def initialize(cache):
        attempts.append(cache)
        if len(attempts)==1:raise TextEmbeddingWarmupError('controlled cold attempt')
        s.ai_ready=True;s.ai_degraded=False;s.refresh_readiness()
    runtime.initialize_ai=initialize
    assert (await runtime.health_check_handler(None)).status==503
    await asyncio.wait_for(runtime.recover_ai('cache'),1)
    assert attempts==['cache','cache'] and s.startup_error is None
    assert (await runtime.health_check_handler(None)).status==200


@pytest.mark.asyncio
async def test_not_ready_message_is_requeued_even_after_old_retry_limit(monkeypatch):
    runtime=worker.WorkerRuntime();incoming=message();incoming.headers={'x-startup-retry-count':999}
    runtime.republish_with_headers=AsyncMock()
    monkeypatch.setattr(worker.asyncio,'sleep',AsyncMock())
    handler=AsyncMock(side_effect=worker.StartupDependencyError('WORKER_NOT_READY'))
    await runtime.smart_retry_wrapper(incoming,handler)
    incoming.reject.assert_awaited_once_with(requeue=True)
    incoming.ack.assert_not_awaited();runtime.republish_with_headers.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_startup_waits_share_one_native_loader_after_timeout(monkeypatch):
    started=threading.Event();release=threading.Event();calls=[]
    def load():
        calls.append(1);started.set();release.wait(2);return 'model'
    monkeypatch.setattr(commerce,'get_embedding_model',load)
    monkeypatch.setattr(commerce,'STARTUP_MODEL_BUDGET_SECONDS',.02)
    monkeypatch.setattr(commerce,'model_registry',SimpleNamespace(reject_text_startup=lambda:None))
    try:
        for _ in range(2):
            with pytest.raises(TextEmbeddingWarmupError):await commerce.initialize_query_embeddings()
        assert started.is_set() and len(calls)==1
    finally:release.set();await asyncio.sleep(.05)


@pytest.mark.asyncio
async def test_loopback_health_transitions_503_to_200_after_background_recovery(monkeypatch):
    from aiohttp import web,ClientSession
    runtime=worker.WorkerRuntime();s=runtime.services
    s.rabbitmq=SimpleNamespace(is_closed=False);s.db_engine=object()
    s.infrastructure_ready=s.consumer_ready=s.payment_ready=True;s.ai_degraded=True
    monkeypatch.setattr(worker,'get_core_settings',lambda:SimpleNamespace(AI_RECOVERY_INTERVAL_SECONDS=.01))
    release=asyncio.Event()
    async def initialize(cache):
        await release.wait();s.ai_ready=True;s.ai_degraded=False;s.refresh_readiness()
    runtime.initialize_ai=initialize
    app=web.Application();app.router.add_get('/health',runtime.health_check_handler)
    runner=web.AppRunner(app);await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1]
    task=asyncio.create_task(runtime.recover_ai(None))
    try:
        async with ClientSession() as client:
            async with client.get(f'http://127.0.0.1:{port}/health') as response:assert response.status==503
            release.set();await asyncio.wait_for(task,1)
            async with client.get(f'http://127.0.0.1:{port}/health') as response:
                assert response.status==200 and (await response.json())['details']['readiness'] is True
    finally:
        release.set();task.cancel();await asyncio.gather(task,return_exceptions=True);await runner.cleanup()


def test_registry_retry_replaces_old_rejection_event_only_under_model_lock(monkeypatch):
    registry=object.__new__(commerce.ModelRegistry)
    registry._text_model=None;registry._model_lock=threading.RLock()
    old=threading.Event();old.set();registry._text_startup_rejected=old
    registry._device='cpu';registry._dtype='float32';registry._text_warmup_status={'state':'failed'}
    model=SimpleNamespace(to=lambda *_:None,eval=lambda:None)
    monkeypatch.setattr(commerce,'SentenceTransformer',lambda *a,**kw:model)
    monkeypatch.setattr(commerce,'warm_text_encoder',lambda *a,**kw:{'state':'ready'})
    assert registry.get_text_model() is model
    assert registry._text_startup_rejected is not old and old.is_set()
    assert not registry._text_startup_rejected.is_set()


@pytest.mark.asyncio
@pytest.mark.skipif(__import__('os').getenv('TEST_RABBITMQ_DISPOSABLE')!='1',reason='dedicated disposable RabbitMQ required')
async def test_real_broker_retains_not_ready_delivery_then_processes_once(monkeypatch):
    import os
    from uuid import uuid4
    import aio_pika
    from app.core.config import CoreSettings
    settings=CoreSettings(RABBITMQ_HOST='127.0.0.1',RABBITMQ_PORT=int(os.getenv('TEST_RABBITMQ_PORT','5672')),
        RABBITMQ_USER='airdeliver_ci',RABBITMQ_PASS='disposable-ci-only')
    connection=await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel=await connection.channel()
    queue=await channel.declare_queue('airdeliver-ci-readiness-'+uuid4().hex,auto_delete=True)
    runtime=worker.WorkerRuntime();ready=False;processed=[]
    monkeypatch.setattr(worker,'get_core_settings',lambda:SimpleNamespace(AI_RECOVERY_INTERVAL_SECONDS=.01))
    async def handler(payload):
        if not ready:raise worker.StartupDependencyError('WORKER_NOT_READY')
        processed.append(payload['user_id'])
    try:
        await channel.default_exchange.publish(aio_pika.Message(body=json.dumps({'user_id':9}).encode(),
            message_id='readiness-recovery-test'),routing_key=queue.name)
        first=await queue.get(timeout=2)
        await runtime.smart_retry_wrapper(first,handler)
        assert processed==[]
        second=await queue.get(timeout=2)
        assert second.redelivered and second.message_id=='readiness-recovery-test'
        ready=True
        await runtime.smart_retry_wrapper(second,handler)
        assert processed==[9]
        assert await queue.get(fail=False,timeout=1) is None
    finally:
        await queue.delete(if_unused=False,if_empty=False)
        await connection.close()


@pytest.mark.asyncio
async def test_shutdown_during_readiness_backoff_retains_original_delivery(monkeypatch):
    runtime=worker.WorkerRuntime();incoming=message();entered=asyncio.Event()
    real_sleep=asyncio.sleep
    async def sleep(delay):
        entered.set();await asyncio.Event().wait()
    monkeypatch.setattr(worker.asyncio,'sleep',sleep)
    task=asyncio.create_task(runtime.smart_retry_wrapper(incoming,
        AsyncMock(side_effect=worker.StartupDependencyError('WORKER_NOT_READY'))))
    await asyncio.wait_for(entered.wait(),1);task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    incoming.reject.assert_awaited_once_with(requeue=True)
    incoming.ack.assert_not_awaited()


def test_inflight_warmup_logs_pending_then_stops_heartbeat_on_failure(caplog):
    import time,logging
    from app.services.embedding_warmup import warm_text_encoder
    caplog.set_level(logging.INFO)
    def encode(*args,**kwargs):
        time.sleep(.04)
        raise ValueError('controlled invalid encoder')
    with pytest.raises(ValueError):
        warm_text_encoder(SimpleNamespace(encode=encode),1536,progress_interval_seconds=.01)
    assert 'warmup sample started attempt=1' in caplog.text
    assert 'state=native_encode_in_flight' in caplog.text
    assert 'model ready' not in caplog.text
    assert not any(t.name=="text-warmup-progress" for t in threading.enumerate())


@pytest.mark.asyncio
async def test_worker_health_responsive_during_native_milvus_retry(monkeypatch):
    import time
    runtime=worker.WorkerRuntime();runtime.services.opensearch_client=object()
    monkeypatch.setattr(worker,'initialize_query_embeddings',AsyncMock(return_value=object()))
    started=threading.Event();release=threading.Event()
    def connect(settings):
        started.set();release.wait(2)
        raise commerce.MilvusConnectionError('controlled outage')
    monkeypatch.setattr(worker,'get_milvus_client',connect)
    task=asyncio.create_task(runtime.initialize_ai(object()))
    try:
        for _ in range(100):
            if started.is_set():break
            await asyncio.sleep(.005)
        assert started.is_set()
        response=await asyncio.wait_for(runtime.health_check_handler(None),.1)
        assert response.status==503 and not runtime.services.ai_ready
    finally:
        release.set()
        with pytest.raises(commerce.MilvusConnectionError):await task
