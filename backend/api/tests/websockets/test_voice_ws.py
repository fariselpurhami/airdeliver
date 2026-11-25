# backend/api/tests/websockets/test_voice_ws.py
"""Characterization tests for the production voice endpoint
/api/v1/ai-ordering/voice-stream (ai_ordering.handle_voice_stream).

Locks in the contract the frontend relies on:
- missing/invalid ticket -> policy-violation close (1008), session never starts
- valid ticket -> orchestrator is constructed with ALL required dependencies
  and the session runs under the ticket's real user id
- a second concurrent session for the same user is rejected (Titanium lock)
"""
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.api import deps
from app.api.v1.endpoints import ai_ordering
from app.services import cache_service

VOICE_URL = "/api/v1/ai-ordering/voice-stream?ticket=t"


class _FakeCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture(scope="module", autouse=True)
def client():
    """TestClient with a no-op lifespan: the real startup connects RabbitMQ
    with a retry loop, which blocks websocket_connect."""
    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    original = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.router.lifespan_context = original


@pytest.fixture
def harness(monkeypatch):
    cache = _FakeCache()
    captured = {}

    async def _fake_session():
        yield object()

    class _StubOrchestrator:
        def __init__(self, **kwargs):
            captured["ctor_kwargs"] = kwargs

        async def process_voice_session(self, websocket, user_id):
            # The real orchestrator accepts the client socket; mirror that or
            # websocket_connect waits for the handshake forever.
            await websocket.accept()
            captured["user_id"] = user_id

    app.dependency_overrides[deps.get_async_session] = _fake_session
    app.dependency_overrides[deps.get_ai_commerce_engine] = lambda: object()
    app.dependency_overrides[deps.get_llm_service] = lambda: object()
    app.dependency_overrides[ai_ordering.get_rabbitmq_service] = lambda: object()
    app.dependency_overrides[cache_service.get_cache_from_request] = lambda: cache
    monkeypatch.setattr(ai_ordering, "AIVoiceOrchestrator", _StubOrchestrator)

    yield SimpleNamespace(cache=cache, captured=captured)
    app.dependency_overrides.clear()


def test_voice_stream_rejects_invalid_ticket(client, harness):
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(VOICE_URL):
            pass
    assert excinfo.value.code == 1008
    assert "ctor_kwargs" not in harness.captured


def test_voice_stream_builds_orchestrator_with_real_user(client, harness):
    harness.cache.store["ws_ticket:t"] = "42"
    with client.websocket_connect(VOICE_URL):
        pass
    assert harness.captured["user_id"] == "42"
    for dep in ("commerce_engine", "llm_service", "rabbitmq", "cache", "db_session"):
        assert dep in harness.captured["ctor_kwargs"], f"missing dependency: {dep}"


def test_voice_stream_rejects_concurrent_session(client, harness):
    harness.cache.store["ws_ticket:t"] = "42"
    harness.cache.store["voice_session_lock:42"] = "active"
    # Locked path accepts first, sends an error frame, then closes with 1008.
    with client.websocket_connect(VOICE_URL) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_text()
    assert excinfo.value.code == 1008
    assert "ctor_kwargs" not in harness.captured
