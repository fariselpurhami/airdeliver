"""Webhook authenticity, raw-byte limits, financial binding and retry behavior."""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from fastapi import HTTPException
from app.core.config import StripeSettings
from app.models.order import Order
from app.api.v1.endpoints import webhooks


def request_for(body, headers=()):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({"type": "http", "method": "POST", "path": "/stripe", "headers": list(headers)}, receive)


def signed_header(body, secret="whsec_dummy"):
    timestamp = int(time.time())
    signature = hmac.new(secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def settings():
    return StripeSettings(STRIPE_SECRET_KEY="sk_test_dummy", STRIPE_WEBHOOK_SECRET="whsec_dummy", STRIPE_PUBLISHABLE_KEY="pk_test_dummy")


@pytest.mark.asyncio
async def test_stripe_signature_uses_real_secret_value_and_raw_bytes():
    body = b'{ "id": "evt_1", "type": "unhandled.event", "data": {"object": {}} }'
    result = await webhooks.stripe_webhook(request_for(body), signed_header(body), settings(), AsyncMock(), AsyncMock(), AsyncMock())
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_stripe_oversize_body_is_rejected_before_signature_verification():
    body = b" " * (262144 + 1)
    with pytest.raises(HTTPException) as caught:
        await webhooks.stripe_webhook(request_for(body), "invalid", settings(), AsyncMock(), AsyncMock(), AsyncMock())
    assert caught.value.status_code == 413


@pytest.mark.asyncio
async def test_stripe_invalid_signature_never_mutates_order():
    db = AsyncMock()
    with pytest.raises(HTTPException) as caught:
        await webhooks.stripe_webhook(request_for(b"{}"), "invalid", settings(), db, AsyncMock(), AsyncMock())
    assert caught.value.status_code == 400
    db.commit.assert_not_awaited()


def payment():
    return {"id": "pi_1", "metadata": {"order_id": "7", "user_id": "42"}, "amount_received": 9950, "currency": "usd"}


@pytest.mark.asyncio
async def test_stripe_processing_failure_is_not_acknowledged_as_success(monkeypatch):
    order = Order(id=7, user_id=42, total_price=99.5, payment_transaction_id="pi_1")
    db = SimpleNamespace(get=AsyncMock(return_value=order))
    completion = SimpleNamespace(finalize_successful_payment=AsyncMock(side_effect=RuntimeError("db unavailable")))
    monkeypatch.setattr(webhooks, "PaymentCompletionService", lambda *args: completion)
    with pytest.raises(RuntimeError, match="db unavailable"):
        await webhooks._delegate_payment_success(payment(), db, AsyncMock(), AsyncMock())


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("amount_received", 1), ("currency", "eur"), ("id", "pi_other")])
async def test_stripe_payment_must_match_local_amount_currency_and_reference(monkeypatch, field, value):
    order = Order(id=7, user_id=42, total_price=99.5, payment_transaction_id="pi_1")
    db = SimpleNamespace(get=AsyncMock(return_value=order))
    completion = SimpleNamespace(finalize_successful_payment=AsyncMock())
    monkeypatch.setattr(webhooks, "PaymentCompletionService", lambda *args: completion)
    intent = payment()
    intent[field] = value
    with pytest.raises(ValueError):
        await webhooks._delegate_payment_success(intent, db, AsyncMock(), AsyncMock())
    completion.finalize_successful_payment.assert_not_awaited()
