"""Worker model lifecycle must follow worker resources, on the same event loop."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import worker_entrypoint as worker


@pytest.mark.asyncio
async def test_initialize_ai_starts_behavior_consolidation(monkeypatch):
    async def opensearch(_):
        yield object()
    behavior = SimpleNamespace(start=AsyncMock())
    monkeypatch.setattr(worker, "get_core_settings", lambda: object())
    monkeypatch.setattr(worker, "get_opensearch_client", opensearch)
    monkeypatch.setattr(worker, "get_milvus_client", Mock(return_value=object()))
    monkeypatch.setattr(worker, "get_embedding_model", Mock(return_value=object()))
    async def commerce_engine(*args):
        return object()
    monkeypatch.setattr(worker, "get_ai_commerce_engine", commerce_engine)
    monkeypatch.setattr(worker, "FreeLLMService", Mock(return_value=object()))
    monkeypatch.setattr(worker, "BehaviorEngine", Mock(return_value=behavior))
    runtime = worker.WorkerRuntime()
    runtime.ensure_milvus_schema = Mock()
    await runtime.initialize_ai(object())
    behavior.start.assert_awaited_once()
    assert runtime.services.ai_ready
    await runtime.services.opensearch_gen.aclose()


@pytest.mark.asyncio
async def test_close_drains_behavior_before_disconnecting_cache():
    events = []
    async def stop():
        events.append("behavior_stop")
    async def disconnect():
        events.append("cache_disconnect")
    runtime = worker.WorkerRuntime()
    runtime.services.behavior = SimpleNamespace(stop=stop)
    runtime.services.cache = SimpleNamespace(disconnect=disconnect)
    await runtime.close()
    await runtime.close()
    assert events == ["behavior_stop", "cache_disconnect"]


@pytest.mark.asyncio
async def test_main_closes_resources_even_when_startup_fails(monkeypatch):
    runtime = SimpleNamespace(main=AsyncMock(side_effect=RuntimeError("startup failed")), close=AsyncMock())
    monkeypatch.setattr(worker, "runtime", runtime)
    with pytest.raises(RuntimeError, match="startup failed"):
        await worker.main()
    runtime.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_outbox_uses_worker_session_and_stops_cleanly(monkeypatch):
    runtime = worker.WorkerRuntime()
    db = object()
    class Context:
        async def __aenter__(self):
            return db
        async def __aexit__(self, *args):
            pass
    runtime.services.session_maker = lambda: Context()
    runtime.services.rabbitmq = object()
    async def dispatch(session, broker, limit):
        assert session is db
        assert broker is runtime.services.rabbitmq
        assert limit == 10
        runtime.shutdown_event.set()
        return SimpleNamespace(sent=2, failed=0)
    monkeypatch.setattr(worker, "dispatch_pending", dispatch)
    await runtime.run_payment_outbox()
    assert runtime.payment_outbox_status["state"] == "running"
    assert runtime.payment_outbox_status["sent"] == 2


@pytest.mark.asyncio
async def test_payment_outbox_exposes_scan_error_without_dying(monkeypatch):
    runtime = worker.WorkerRuntime()
    class Context:
        async def __aenter__(self):
            runtime.shutdown_event.set()
            raise RuntimeError("database unavailable")
        async def __aexit__(self, *args):
            pass
    runtime.services.session_maker = lambda: Context()
    runtime.services.rabbitmq = object()
    await runtime.run_payment_outbox()
    assert runtime.payment_outbox_status == {"state": "error", "error_type": "RuntimeError"}


def test_payment_initialization_accepts_only_configured_real_gateway(monkeypatch):
    from pydantic import ValidationError
    from app.core.config import StripeSettings
    from app.services.payment_orchestrator import GatewayProvider
    runtime = worker.WorkerRuntime()
    runtime.services.http_client = object()
    monkeypatch.setattr(worker, "get_stripe_settings", lambda: StripeSettings(
        STRIPE_SECRET_KEY="sk_test_dummy", STRIPE_WEBHOOK_SECRET="whsec_dummy", STRIPE_PUBLISHABLE_KEY="pk_test_dummy"))
    def missing():
        raise ValidationError.from_exception_data("UnconfiguredGateway", [])
    monkeypatch.setattr(worker, "get_paypal_settings", missing)
    monkeypatch.setattr(worker, "get_mpesa_settings", missing)
    runtime.initialize_payment(object())
    assert runtime.services.payment_ready is True
    assert set(runtime.services.payment._gateways) == {GatewayProvider.STRIPE}


def test_payment_initialization_rejects_no_configured_gateway(monkeypatch):
    from pydantic import ValidationError
    runtime = worker.WorkerRuntime()
    runtime.services.http_client = object()
    def missing():
        raise ValidationError.from_exception_data("UnconfiguredGateway", [])
    for name in ("get_stripe_settings", "get_paypal_settings", "get_mpesa_settings"):
        monkeypatch.setattr(worker, name, missing)
    with pytest.raises(worker.StartupDependencyError, match="No payment gateway"):
        runtime.initialize_payment(object())
    assert runtime.services.payment_ready is False
