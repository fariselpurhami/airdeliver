# apps/api/tests/test_rabbitmq_service.py
"""Tests for RabbitMQService publish contract (broker mocked)."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.rabbitmq_service import (
    PublishOutcome,
    PublishResult,
    RabbitMQService,
)
from app.core.config import settings


class FakeExchange:
    def __init__(self, confirmation=True, exc=None):
        self._confirmation = confirmation
        self._exc = exc
        self.published = []

    async def publish(self, message, routing_key, timeout=None):
        if self._exc:
            raise self._exc
        self.published.append((message, routing_key))
        return self._confirmation


def make_service():
    return RabbitMQService(settings)


# --- pure dataclass contract ---

def test_publish_outcome_success_only_when_confirmed():
    base = dict(routing_key="rk", correlation_id="c", attempts=1, elapsed_ms=1.0)
    assert PublishOutcome(result=PublishResult.CONFIRMED, **base).is_success
    for r in (PublishResult.NACKED, PublishResult.EXHAUSTED, PublishResult.SERIALIZATION_ERROR):
        assert not PublishOutcome(result=r, **base).is_success


# --- publish paths ---

@pytest.mark.asyncio
async def test_publish_confirmed_message():
    svc = make_service()
    exchange = FakeExchange(confirmation=True)
    with patch.object(svc, "_ensure_exchange", new=AsyncMock(return_value=exchange)):
        outcome = await svc.publish({"hello": "world"}, "test.rk", correlation_id="corr-1")
    assert outcome.result == PublishResult.CONFIRMED
    assert outcome.is_success and outcome.correlation_id == "corr-1"
    message, rk = exchange.published[0]
    assert rk == "test.rk"
    assert json.loads(message.body) == {"hello": "world"}
    assert message.delivery_mode is not None  # persistent


@pytest.mark.asyncio
async def test_publish_nack_is_not_success():
    svc = make_service()
    exchange = FakeExchange(confirmation=False)
    with patch.object(svc, "_ensure_exchange", new=AsyncMock(return_value=exchange)):
        outcome = await svc.publish({"a": 1}, "rk", correlation_id="c2")
    assert outcome.result == PublishResult.NACKED
    assert not outcome.is_success


@pytest.mark.asyncio
async def test_publish_retries_then_exhausts():
    svc = make_service()
    exchange = FakeExchange(exc=ConnectionError("broker down"))
    with patch.object(svc, "_ensure_exchange", new=AsyncMock(return_value=exchange)):
        outcome = await svc.publish({"a": 1}, "rk", max_retries=2)
    assert outcome.result == PublishResult.EXHAUSTED
    assert outcome.attempts == 2
    assert not outcome.is_success


@pytest.mark.asyncio
async def test_publish_generates_correlation_id_when_missing():
    svc = make_service()
    exchange = FakeExchange()
    with patch.object(svc, "_ensure_exchange", new=AsyncMock(return_value=exchange)):
        outcome = await svc.publish({"a": 1}, "rk")
    assert outcome.correlation_id, "a correlation id must be generated"
    message, _ = exchange.published[0]
    assert message.correlation_id == outcome.correlation_id


@pytest.mark.asyncio
async def test_publish_handles_non_serializable_body():
    svc = make_service()
    class Unserializable:
        def __str__(self):
            raise ValueError("nope")
    # json.dumps(default=str) will call str() which raises -> serialization error path
    outcome = await svc.publish({"bad": Unserializable()}, "rk")
    assert outcome.result == PublishResult.SERIALIZATION_ERROR
    assert outcome.attempts == 0


@pytest.mark.asyncio
async def test_is_healthy_without_connection():
    svc = make_service()
    assert await svc.is_healthy() is False
