# apps/api/tests/test_support_endpoint.py
"""Tests for the ai_support /chat POST endpoint abuse control and wiring."""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import ai_support
from app.api.v1.endpoints.ai_support import (
    RATE_LIMIT_MAX_MESSAGES,
    check_support_rate_limit,
)
from app.main import app
from app.schemas.ai_actions import NeuralCoreResponse
from app.services.cache_service import get_cache_from_request
from app.services.neural_core_service import get_neural_core_service

pytestmark = pytest.mark.anyio


class CountingCache:
    """In-memory cache implementing just incr/expire for rate-limit tests."""

    def __init__(self):
        self.counts = {}
        self.fail = False

    async def incr(self, key):
        if self.fail:
            raise RuntimeError("cache down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, ttl):
        if self.fail:
            raise RuntimeError("cache down")


class StubNeuralService:
    last_image_base64 = "UNSET"

    async def handle_message(self, db, message, user, session_id, image_base64=None):
        StubNeuralService.last_image_base64 = image_base64
        return NeuralCoreResponse(
            text="stub reply",
            explain="stub",
            confidence=0.5,
            telemetry={"intent": "SOCIAL_CHAT", "entities": [], "turn": 0},
        )


class TestRateLimitHelper:
    async def test_allows_up_to_the_limit(self):
        cache = CountingCache()
        for _ in range(RATE_LIMIT_MAX_MESSAGES):
            assert await check_support_rate_limit("user:1", cache) is True

    async def test_blocks_after_the_limit(self):
        cache = CountingCache()
        for _ in range(RATE_LIMIT_MAX_MESSAGES):
            await check_support_rate_limit("user:1", cache)
        assert await check_support_rate_limit("user:1", cache) is False

    async def test_clients_are_isolated(self):
        cache = CountingCache()
        for _ in range(RATE_LIMIT_MAX_MESSAGES + 1):
            await check_support_rate_limit("user:1", cache)
        assert await check_support_rate_limit("user:2", cache) is True

    async def test_fail_open_on_cache_failure(self):
        cache = CountingCache()
        cache.fail = True
        assert await check_support_rate_limit("user:1", cache) is True


class TestSupportEndpoint:
    @pytest.fixture
    def client(self):
        cache = CountingCache()
        app.dependency_overrides[get_neural_core_service] = lambda: StubNeuralService()
        app.dependency_overrides[get_cache_from_request] = lambda: cache
        # No `with` block: entering the context manager runs the app lifespan,
        # which connects to Postgres/Redis/RabbitMQ. Route tests don't need it.
        yield TestClient(app), cache
        app.dependency_overrides.clear()

    def _post(self, client, session="session-abc"):
        return client.post(
            "/api/v1/ai-support/chat",
            json={"message": "hello there", "session_id": session},
        )

    def test_happy_path_returns_neural_response(self, client):
        test_client, _ = client
        resp = self._post(test_client)
        assert resp.status_code == 200
        assert resp.json()["text"] == "stub reply"

    def test_rate_limit_returns_429_after_threshold(self, client):
        test_client, _ = client
        for _ in range(RATE_LIMIT_MAX_MESSAGES):
            resp = self._post(test_client)
            assert resp.status_code == 200
        resp = self._post(test_client)
        assert resp.status_code == 429

    def test_message_size_bound_enforced(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/api/v1/ai-support/chat",
            json={"message": "x" * 4097, "session_id": "session-abc"},
        )
        assert resp.status_code == 422

    def test_image_only_request_is_accepted(self, client):
        test_client, _ = client
        StubNeuralService.last_image_base64 = "UNSET"
        resp = test_client.post(
            "/api/v1/ai-support/chat",
            json={"message": "", "session_id": "session-abc", "image_base64": "aGVsbG8="},
        )
        assert resp.status_code == 200
        assert StubNeuralService.last_image_base64 == "aGVsbG8="

    def test_empty_message_without_image_is_rejected(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/api/v1/ai-support/chat",
            json={"message": "   ", "session_id": "session-abc"},
        )
        assert resp.status_code == 422

    def test_image_size_bound_enforced(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/api/v1/ai-support/chat",
            json={
                "message": "what is this?",
                "session_id": "session-abc",
                "image_base64": "x" * 7_000_001,
            },
        )
        assert resp.status_code == 422

    def test_session_id_pattern_enforced(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/api/v1/ai-support/chat",
            json={"message": "hi", "session_id": "bad session!"},
        )
        assert resp.status_code == 422
