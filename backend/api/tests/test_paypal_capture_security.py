"""PayPal capture must match server-owned order facts before any capture POST."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr
from app.services.payment_orchestrator import PayPalGateway, PaymentStatus


def order_body(status="APPROVED"):
    body = {"id": "PP123", "intent": "CAPTURE", "status": status, "purchase_units": [{
        "reference_id": "7", "custom_id": "42", "amount": {"currency_code": "USD", "value": "99.50"}}]}
    if status == "COMPLETED":
        body["purchase_units"][0]["payments"] = {"captures": [{"id": "CAP123", "status": "COMPLETED", "amount": {"currency_code": "USD", "value": "99.50"}}]}
    return body


def gateway(details):
    calls = []
    def transport(request):
        calls.append(request)
        return httpx.Response(200, json=details if request.method == "GET" else order_body("COMPLETED"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    settings = SimpleNamespace(PAYPAL_CLIENT_ID="cid", PAYPAL_CLIENT_SECRET=SecretStr("dummy"),
                               PAYPAL_API_BASE_URL="https://api-m.sandbox.paypal.com", PAYPAL_WEBHOOK_ID="WH123")
    cache = SimpleNamespace(get=AsyncMock(return_value="cached-token"), set=AsyncMock())
    return PayPalGateway(settings, cache, client), client, calls


async def capture(gateway):
    return await gateway.capture_order("PP123", expected_order_id=7, expected_user_id=42,
                                       expected_amount=Decimal("99.50"), expected_currency="USD")


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("reference_id", "8"), ("custom_id", "99"), ("value", "0.01"), ("currency_code", "EUR")])
async def test_mismatched_provider_order_is_never_captured(field, value):
    details = order_body()
    unit = details["purchase_units"][0]
    (unit["amount"] if field in {"value", "currency_code"} else unit)[field] = value
    gw, client, calls = gateway(details)
    async with client:
        result = await capture(gw)
    assert result.status == PaymentStatus.FAILURE
    assert [call.method for call in calls] == ["GET"]


@pytest.mark.asyncio
async def test_verified_capture_is_idempotency_bound_and_financially_checked():
    gw, client, calls = gateway(order_body())
    async with client:
        result = await capture(gw)
    assert result.status == PaymentStatus.SUCCESS
    assert [call.method for call in calls] == ["GET", "POST"]
    assert calls[1].headers["PayPal-Request-Id"]
    assert calls[1].headers["Prefer"] == "return=representation"


@pytest.mark.asyncio
async def test_completed_order_is_reconciled_without_recapture():
    gw, client, calls = gateway(order_body("COMPLETED"))
    async with client:
        result = await capture(gw)
    assert result.status == PaymentStatus.SUCCESS
    assert [call.method for call in calls] == ["GET"]


@pytest.mark.asyncio
async def test_completed_status_without_completed_funds_is_not_success():
    details = order_body("COMPLETED")
    details["purchase_units"][0]["payments"]["captures"][0]["status"] = "PENDING"
    gw, client, calls = gateway(details)
    async with client:
        result = await capture(gw)
    assert result.status == PaymentStatus.FAILURE
    assert [call.method for call in calls] == ["GET"]


@pytest.mark.asyncio
async def test_capture_order_id_cannot_inject_url_path():
    gw, client, calls = gateway(order_body())
    async with client:
        result = await gw.capture_order("../other", expected_order_id=7, expected_user_id=42,
                                        expected_amount=Decimal("99.50"), expected_currency="USD")
    assert result.status == PaymentStatus.FAILURE
    assert calls == []


def test_completed_funds_cannot_double_count_duplicate_capture_identifiers():
    details=order_body('COMPLETED')
    capture=details['purchase_units'][0]['payments']['captures'][0]
    capture['amount']['value']='49.75'
    import copy
    details['purchase_units'][0]['payments']['captures'].append(copy.deepcopy(capture))
    with pytest.raises(ValueError,match='unique'):
        PayPalGateway.validate_order_details(details,'PP123',expected_order_id=7,expected_user_id=42,expected_amount=Decimal('99.50'),expected_currency='USD',require_completed=True)


def test_distinct_completed_captures_with_exact_total_remain_supported():
    details=order_body('COMPLETED')
    details['purchase_units'][0]['payments']['captures']=[
        {'id':'CAP1','status':'COMPLETED','amount':{'currency_code':'USD','value':'49.75'}},
        {'id':'CAP2','status':'COMPLETED','amount':{'currency_code':'USD','value':'49.75'}},
    ]
    PayPalGateway.validate_order_details(details,'PP123',expected_order_id=7,expected_user_id=42,expected_amount=Decimal('99.50'),expected_currency='USD',require_completed=True)
