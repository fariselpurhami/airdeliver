from types import SimpleNamespace
from unittest.mock import AsyncMock
import json
import httpx
import pytest
from fastapi import HTTPException
from app.api.v1.endpoints import webhooks
from app.models.order import Order
from tests.test_webhook_security import request_for
from tests.test_paypal_capture_security import order_body, gateway

HEADERS = {"paypal-auth-algo": "SHA256withRSA", "paypal-cert-url": "https://api.paypal.com/cert",
           "paypal-transmission-id": "T123", "paypal-transmission-sig": "sig", "paypal-transmission-time": "2026-11-22T17:00:00Z"}


@pytest.mark.asyncio
async def test_webhook_signature_is_verified_by_paypal_api():
    gw, client, calls = gateway(order_body())
    async def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"verification_status": "SUCCESS"})
    client._transport = httpx.MockTransport(handle)
    async with client:
        assert await gw.verify_webhook_signature({"id": "EV123"}, HEADERS)
    payload = json.loads(calls[0].content)
    assert payload["webhook_id"] == "WH123"
    assert payload["webhook_event"] == {"id": "EV123"}
    assert calls[0].url.path == "/v1/notifications/verify-webhook-signature"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_missing_signature_headers_never_call_provider():
    gw, client, calls = gateway(order_body())
    async with client:
        assert not await gw.verify_webhook_signature({}, {})
    assert calls == []


def event():
    return {"event_type": "PAYMENT.CAPTURE.COMPLETED", "id": "EV123", "resource": {
        "id": "CAP123", "status": "COMPLETED", "supplementary_data": {"related_ids": {"order_id": "PP123"}}}}


@pytest.mark.asyncio
@pytest.mark.parametrize("signature_ok", [False, True])
async def test_paypal_webhook_requires_verified_signature_and_order(monkeypatch, signature_ok):
    details = order_body("COMPLETED")
    fake = SimpleNamespace(verify_webhook_signature=AsyncMock(return_value=signature_ok),
                           get_order_details=AsyncMock(return_value=details),
                           validate_order_details=webhooks.PayPalGateway.validate_order_details)
    completion = SimpleNamespace(finalize_successful_payment=AsyncMock())
    monkeypatch.setattr(webhooks, "PayPalGateway", lambda *args: fake)
    monkeypatch.setattr(webhooks, "PaymentCompletionService", lambda *args: completion)
    db = SimpleNamespace(get=AsyncMock(return_value=Order(id=7, user_id=42, total_price=99.5, payment_transaction_id="PP123")))
    request = request_for(json.dumps(event()).encode())
    if signature_ok:
        response = await webhooks.paypal_webhook(request, SimpleNamespace(PAYPAL_WEBHOOK_ID="WH123"), db, AsyncMock(), AsyncMock())
        assert response["status"] == "success"
        completion.finalize_successful_payment.assert_awaited_once_with(7, 42, "PP123")
    else:
        with pytest.raises(HTTPException) as caught:
            await webhooks.paypal_webhook(request, SimpleNamespace(PAYPAL_WEBHOOK_ID="WH123"), db, AsyncMock(), AsyncMock())
        assert caught.value.status_code == 400
        fake.get_order_details.assert_not_awaited()
        completion.finalize_successful_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_paypal_unconfigured_webhook_fails_closed():
    with pytest.raises(HTTPException) as caught:
        await webhooks.paypal_webhook(request_for(b"{}"), SimpleNamespace(PAYPAL_WEBHOOK_ID=None), AsyncMock(), AsyncMock(), AsyncMock())
    assert caught.value.status_code == 503
