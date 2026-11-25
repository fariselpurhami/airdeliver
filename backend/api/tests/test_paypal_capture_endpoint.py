from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from app.api.v1.endpoints import ai_ordering
from app.models.order import Order
from app.services.payment_orchestrator import PaymentStatus
from tests.test_webhook_security import request_for


@pytest.mark.asyncio
async def test_capture_rejects_unbound_payment_before_contacting_paypal(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(ai_ordering, "PayPalGateway", factory)
    order = Order(id=7, user_id=42, total_price=99.5, payment_transaction_id="PP123")
    db = SimpleNamespace(get=AsyncMock(return_value=order))
    with pytest.raises(HTTPException) as caught:
        await unwrap(ai_ordering.capture_paypal_order)(request_for(b""), ai_ordering.PayPalCaptureRequest(order_id="7", paypal_order_id="OTHER"),
             SimpleNamespace(id=42), db, AsyncMock(), AsyncMock())
    assert caught.value.status_code == 409
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_capture_passes_server_owned_financial_facts(monkeypatch):
    capture = AsyncMock(return_value=SimpleNamespace(status=PaymentStatus.SUCCESS))
    def factory(settings, cache, client):
        return SimpleNamespace(capture_order=capture, _http_client=client)
    completion = SimpleNamespace(finalize_successful_payment=AsyncMock())
    monkeypatch.setattr(ai_ordering, "PayPalGateway", factory)
    monkeypatch.setattr(ai_ordering, "get_paypal_settings", lambda: object())
    monkeypatch.setattr(ai_ordering, "PaymentCompletionService", lambda *args: completion)
    order = Order(id=7, user_id=42, total_price=99.5, payment_transaction_id="PP123")
    db = SimpleNamespace(get=AsyncMock(return_value=order))
    response = await unwrap(ai_ordering.capture_paypal_order)(request_for(b""), ai_ordering.PayPalCaptureRequest(order_id="7", paypal_order_id="PP123"),
             SimpleNamespace(id=42), db, AsyncMock(), AsyncMock())
    assert response["status"] == "captured"
    assert capture.await_args.kwargs["expected_order_id"] == 7
    assert capture.await_args.kwargs["expected_user_id"] == 42
    assert str(capture.await_args.kwargs["expected_amount"]) == "99.5"
    completion.finalize_successful_payment.assert_awaited_once()
