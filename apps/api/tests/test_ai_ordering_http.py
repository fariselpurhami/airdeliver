# apps/api/tests/test_ai_ordering_http.py
"""Tests for the HTTP cart/checkout command endpoints in ai_ordering.

These endpoints are the single consumer path for cart/checkout commands
(previously published to RabbitMQ queues with no worker). Tests verify
payload plumbing into AICartService / AICheckoutService and the honest
503 when no payment gateway is configured.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints import ai_ordering
from app.main import app

pytestmark = pytest.mark.anyio


FAKE_USER = SimpleNamespace(id=1, email="user@test.local", address=None)


class RecordingCartService:
    def __init__(self):
        self.calls = []

    async def handle_sync_cart(self, payload):
        self.calls.append(("sync", payload))

    async def handle_add_to_cart(self, payload):
        self.calls.append(("add", payload))

    async def handle_remove_from_cart(self, payload):
        self.calls.append(("remove", payload))

    async def handle_clear_cart(self, payload):
        self.calls.append(("clear", payload))

    async def handle_save_cart(self, payload):
        self.calls.append(("save", payload))


class RecordingNluService:
    def __init__(self):
        self.calls = []

    async def process_message(self, payload):
        self.calls.append(payload)


class RecordingCheckoutService:
    def __init__(self):
        self.calls = []

    async def handle_confirm_order(self, payload):
        self.calls.append(("confirm", payload))

    async def handle_cancel_order(self, payload):
        self.calls.append(("cancel", payload))


@pytest.fixture
def client():
    cart = RecordingCartService()
    checkout = RecordingCheckoutService()
    app.dependency_overrides[deps.get_current_active_user] = lambda: FAKE_USER
    app.dependency_overrides[ai_ordering.get_ai_cart_service] = lambda: cart
    app.dependency_overrides[ai_ordering.get_ai_checkout_service] = lambda: checkout
    nlu = RecordingNluService()
    app.dependency_overrides[ai_ordering.get_ai_nlu_service] = lambda: nlu
    # NOTE: no `with` - TestClient lifespan startup hangs in this suite.
    yield TestClient(app, raise_server_exceptions=True), cart, checkout, nlu
    app.dependency_overrides.clear()


class TestCartEndpoints:
    def test_add_to_cart_plumbs_user_and_product(self, client):
        c, cart, _, _nlu = client
        resp = c.post("/api/v1/ai-ordering/cart/add", json={"product_id": 5, "quantity": 2})
        assert resp.status_code == 202
        assert cart.calls == [("add", {"user_id": 1, "product_id": 5, "quantity": 2})]

    def test_add_to_cart_rejects_zero_quantity(self, client):
        c, cart, _, _nlu = client
        resp = c.post("/api/v1/ai-ordering/cart/add", json={"product_id": 5, "quantity": 0})
        assert resp.status_code == 422
        assert cart.calls == []

    def test_remove_from_cart(self, client):
        c, cart, _, _nlu = client
        resp = c.post("/api/v1/ai-ordering/cart/remove", json={"product_id": 7})
        assert resp.status_code == 202
        assert cart.calls == [("remove", {"user_id": 1, "product_id": 7})]

    def test_clear_cart(self, client):
        c, cart, _, _nlu = client
        resp = c.post("/api/v1/ai-ordering/cart/clear")
        assert resp.status_code == 202
        assert cart.calls == [("clear", {"user_id": 1})]

    def test_save_cart(self, client):
        c, cart, _, _nlu = client
        resp = c.post("/api/v1/ai-ordering/cart/save")
        assert resp.status_code == 202
        assert cart.calls == [("save", {"user_id": 1})]

    def test_sync_cart(self, client):
        c, cart, _, _nlu = client
        resp = c.post("/api/v1/ai-ordering/cart/sync")
        assert resp.status_code == 202
        assert cart.calls == [("sync", {"user_id": 1})]


class TestCheckoutEndpoints:
    def test_confirm_order_injects_user_context(self, client):
        c, _, checkout, _nlu = client
        resp = c.post("/api/v1/ai-ordering/checkout/confirm", json={})
        assert resp.status_code == 202
        name, payload = checkout.calls[0]
        assert name == "confirm"
        assert payload["user_id"] == 1
        assert payload["email"] == "user@test.local"
        assert payload["country"] == "US"

    def test_cancel_order_forwards_order_id(self, client):
        c, _, checkout, _nlu = client
        resp = c.post("/api/v1/ai-ordering/checkout/cancel", json={"order_id": 42})
        assert resp.status_code == 202
        assert checkout.calls == [("cancel", {"user_id": 1, "order_id": 42})]


class TestSessionEndpoints:
    def test_suggestions_routes_to_nlu_pipeline(self, client):
        c, _, _, nlu = client
        resp = c.post("/api/v1/ai-ordering/session/suggestions")
        assert resp.status_code == 202
        assert len(nlu.calls) == 1
        payload = nlu.calls[0]
        assert payload["user_id"] == 1
        assert payload["message"] == "__INTERNAL_GET_INITIAL_SUGGESTIONS__"
        assert payload["type"] == "CHAT_MESSAGE"

    def test_reset_routes_to_nlu_pipeline(self, client):
        c, _, _, nlu = client
        resp = c.post("/api/v1/ai-ordering/session/reset")
        assert resp.status_code == 202
        assert len(nlu.calls) == 1
        assert nlu.calls[0]["message"] == "__INTERNAL_RESET_SESSION__"


class TestCheckoutServiceProvider:
    """The real dependency provider, exercised directly (no FastAPI)."""

    async def _collect(self, agen):
        service = await agen.__anext__()
        try:
            return service
        finally:
            await agen.aclose()

    async def test_no_gateways_configured_is_honest_503(self, monkeypatch):
        # Settings load from the repo .env, so simulate a deployment with no
        # payment configuration by making every settings factory fail.
        def _missing():
            raise ValueError("settings not configured")

        monkeypatch.setattr(ai_ordering, "get_stripe_settings", _missing)
        monkeypatch.setattr(ai_ordering, "get_paypal_settings", _missing)
        monkeypatch.setattr(ai_ordering, "get_mpesa_settings", _missing)

        agen = ai_ordering.get_ai_checkout_service(db=None, cache=None, rabbitmq=None)
        with pytest.raises(HTTPException) as exc_info:
            await agen.__anext__()
        assert exc_info.value.status_code == 503
        await agen.aclose()

    async def test_stripe_only_env_yields_working_service(self, monkeypatch):
        from app.core.config import StripeSettings

        monkeypatch.setattr(
            ai_ordering,
            "get_stripe_settings",
            lambda: StripeSettings(
                STRIPE_SECRET_KEY="sk_test_dummy",
                STRIPE_WEBHOOK_SECRET="whsec_dummy",
                STRIPE_PUBLISHABLE_KEY="pk_test_dummy",
            ),
        )

        def _missing():
            raise ValueError("settings not configured")

        monkeypatch.setattr(ai_ordering, "get_paypal_settings", _missing)
        monkeypatch.setattr(ai_ordering, "get_mpesa_settings", _missing)

        agen = ai_ordering.get_ai_checkout_service(db=None, cache=None, rabbitmq=None)
        service = await agen.__anext__()
        await agen.aclose()
        from app.services.payment_orchestrator import GatewayProvider
        assert GatewayProvider.STRIPE in service.orchestrator._gateways
        assert len(service.orchestrator._gateways) == 1
