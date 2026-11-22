"""PayPal gateway: token caching, order creation, error mapping (mocked HTTP)."""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.payment_orchestrator import (
    GatewayProvider,
    PaymentRequest,
    PaymentStatus,
    PayPalGateway,
)


def make_gateway(api_body=None, api_status=200, token_cached=None):
    settings = MagicMock()
    settings.PAYPAL_CLIENT_ID = "cid"
    settings.PAYPAL_CLIENT_SECRET = MagicMock()
    settings.PAYPAL_CLIENT_SECRET.get_secret_value.return_value = "secret"
    settings.PAYPAL_API_BASE_URL = "https://api-m.sandbox.paypal.com"

    cache = AsyncMock()
    cache.get = AsyncMock(return_value=token_cached)

    def make_resp(status, body):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = body
        resp.raise_for_status = MagicMock()
        if status >= 400:
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "err", request=MagicMock(), response=resp
            )
        return resp

    http_client = AsyncMock()
    if token_cached is None:
        # First call is the OAuth token fetch, second is the order create.
        token_resp = make_resp(200, {"access_token": "fresh-token", "expires_in": 300})
        http_client.post = AsyncMock(
            side_effect=[token_resp, make_resp(api_status, api_body or {})]
        )
    else:
        http_client.post = AsyncMock(return_value=make_resp(api_status, api_body or {}))
    return PayPalGateway(settings, cache, http_client), http_client, cache


def make_request():
    return PaymentRequest(
        order_id="7", amount="99.50", currency="USD", region="US",
        idempotency_key="idem-1234567890abcdef", metadata={"user_id": "42"},
    )


@pytest.mark.asyncio
async def test_creates_order_and_returns_approval_link():
    body = {
        "id": "PAYPAL-ORDER-1",
        "links": [
            {"rel": "self", "href": "https://x/self"},
            {"rel": "approve", "href": "https://paypal/approve"},
        ],
    }
    gw, http_client, cache = make_gateway(api_body=body)
    result = await gw.create_payment_intent(make_request())

    assert result.provider == GatewayProvider.PAYPAL
    assert result.status == PaymentStatus.REQUIRES_ACTION
    assert result.transaction_id == "PAYPAL-ORDER-1"
    assert result.action_url == "https://paypal/approve"
    # token fetch happened (no cached token) then order create
    assert http_client.post.await_count == 2
    order_call = http_client.post.await_args_list[1]
    assert order_call.kwargs["headers"]["PayPal-Request-Id"] == "idem-1234567890abcdef"
    unit = order_call.kwargs["json"]["purchase_units"][0]
    assert unit["reference_id"] == "7"
    assert unit["custom_id"] == "42"


@pytest.mark.asyncio
async def test_cached_token_skips_oauth_call():
    body = {"id": "X", "links": [{"rel": "approve", "href": "https://paypal/ok"}]}
    gw, http_client, _ = make_gateway(api_body=body, token_cached="cached-token")
    await gw.create_payment_intent(make_request())
    assert http_client.post.await_count == 1  # only the order call
    headers = http_client.post.await_args_list[0].kwargs["headers"]
    assert headers["Authorization"] == "Bearer cached-token"


@pytest.mark.asyncio
async def test_api_error_maps_to_failure():
    gw, _, _ = make_gateway(api_status=500, token_cached="t")
    result = await gw.create_payment_intent(make_request())
    assert result.status == PaymentStatus.FAILURE


@pytest.mark.asyncio
async def test_missing_approval_link_is_failure():
    gw, _, _ = make_gateway(api_body={"id": "X", "links": []}, token_cached="t")
    result = await gw.create_payment_intent(make_request())
    assert result.status == PaymentStatus.FAILURE
    assert "approval link" in (result.error_message or "")
