# apps/api/tests/test_ai_checkout_service.py
"""
Unit tests for AICheckoutService: the money-critical chat checkout path.

Uses in-memory fakes for the DB session, cache, RabbitMQ and the payment
orchestrator so the full confirm/success/cancel state machine is exercised
without infrastructure.
"""
import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.enums import OrderStatus
from app.models.order import Order
from app.services.ai_checkout_service import AICheckoutService
from app.services.payment_orchestrator import PaymentStatus


class FakeCache:
    def __init__(self, cart=None):
        self._cart = cart
        self.published = []
        self.deleted = []

    async def get_json(self, key):
        return self._cart

    async def publish(self, channel, message):
        self.published.append((channel, json.loads(message)))

    async def delete(self, key):
        self.deleted.append(key)


class FakeDB:
    """Mimics the AsyncSession surface the service uses."""

    def __init__(self, order=None):
        self._order = order
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self._next_id = 42

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, Order) and obj.id is None:
            obj.id = self._next_id

    def add_all(self, objs):
        for o in objs:
            self.add(o)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        pass

    async def rollback(self):
        self.rollbacks += 1

    async def get(self, model, pk):
        if self._order is not None and self._order.id == pk:
            return self._order
        return None


class FakeRabbit:
    def __init__(self):
        self.events = []

    async def publish(self, payload, routing_key):
        self.events.append((routing_key, payload))


def make_orchestrator(status=PaymentStatus.SUCCESS, client_secret="sec_123", action_url=None, exc=None):
    orch = SimpleNamespace()
    if exc is not None:
        orch.process_payment = AsyncMock(side_effect=exc)
    else:
        gateway = SimpleNamespace(client_secret=client_secret, action_url=action_url, provider="stripe", transaction_id="pi_test")
        resp = SimpleNamespace(status=status, primary_gateway=gateway, error_message="declined" if status != PaymentStatus.SUCCESS else None)
        orch.process_payment = AsyncMock(return_value=resp)
    return orch


def make_service(cart=None, order=None, orchestrator=None):
    cache = FakeCache(cart)
    db = FakeDB(order)
    rabbit = FakeRabbit()
    orch = orchestrator or make_orchestrator()
    svc = AICheckoutService(db=db, cache=cache, rabbitmq=rabbit, orchestrator=orch)
    return svc, cache, db, rabbit, orch


CART = {"items": [{"product_id": 7, "name": "Shoes", "quantity": 2, "price": "10.50"}]}
CONFIRM = {"user_id": 1, "address": "12 Nile St", "country": "EG", "email": "u@example.com"}


@pytest.mark.asyncio
async def test_confirm_order_happy_path_creates_order_and_payment_intent():
    svc, cache, db, rabbit, orch = make_service(cart=dict(CART))
    await svc.handle_confirm_order(dict(CONFIRM))

    orders = [o for o in db.added if isinstance(o, Order)]
    assert orders, "an Order should have been persisted"
    assert orders[0].status == OrderStatus.PENDING
    assert Decimal(str(orders[0].total_price)) == Decimal("21.00")
    assert db.commits >= 1
    orch.process_payment.assert_awaited_once()
    # UI receives the payment intent with client_secret but no raw gateway response
    intents = [p for _, p in cache.published if p.get("type") == "payment_intent"]
    assert intents and intents[0]["content"]["client_secret"] == "sec_123"
    assert "raw_response" not in json.dumps(intents[0])


@pytest.mark.asyncio
async def test_confirm_order_empty_cart_sends_error_no_db_writes():
    svc, cache, db, rabbit, orch = make_service(cart={"items": []})
    await svc.handle_confirm_order(dict(CONFIRM))
    assert not db.added
    orch.process_payment.assert_not_called()
    errors = [p for _, p in cache.published if p.get("type") == "error"]
    assert errors


@pytest.mark.asyncio
async def test_confirm_order_invalid_payload_is_rejected():
    svc, cache, db, rabbit, orch = make_service(cart=dict(CART))
    await svc.handle_confirm_order({"user_id": "not-an-int"})
    assert not db.added
    orch.process_payment.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_order_corrupt_price_rolls_back():
    bad_cart = {"items": [{"product_id": 7, "quantity": 1, "price": "not-a-number"}]}
    svc, cache, db, rabbit, orch = make_service(cart=bad_cart)
    await svc.handle_confirm_order(dict(CONFIRM))
    assert db.rollbacks >= 1 or not db.added
    orch.process_payment.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_order_gateway_decline_marks_order_failed():
    orch = make_orchestrator(status=PaymentStatus.FAILURE)
    svc, cache, db, rabbit, _ = make_service(cart=dict(CART), orchestrator=orch)
    await svc.handle_confirm_order(dict(CONFIRM))
    orders = [o for o in db.added if isinstance(o, Order)]
    assert orders[0].status == OrderStatus.FAILED


@pytest.mark.asyncio
async def test_confirm_order_gateway_timeout_marks_failed():
    orch = make_orchestrator(exc=asyncio.TimeoutError())
    svc, cache, db, rabbit, _ = make_service(cart=dict(CART), orchestrator=orch)
    await svc.handle_confirm_order(dict(CONFIRM))
    orders = [o for o in db.added if isinstance(o, Order)]
    assert orders[0].status == OrderStatus.FAILED


@pytest.mark.asyncio
async def test_confirm_order_success_without_tokens_is_treated_as_failure():
    orch = make_orchestrator(status=PaymentStatus.SUCCESS, client_secret=None, action_url=None)
    svc, cache, db, rabbit, _ = make_service(cart=dict(CART), orchestrator=orch)
    await svc.handle_confirm_order(dict(CONFIRM))
    orders = [o for o in db.added if isinstance(o, Order)]
    assert orders[0].status == OrderStatus.FAILED
    intents = [p for _, p in cache.published if p.get("type") == "payment_intent"]
    assert not intents


@pytest.mark.asyncio
async def test_payment_success_marks_paid_and_clears_cart():
    order = Order(id=9, user_id=1, status=OrderStatus.PENDING, total_price=21.0, delivery_address="x")
    svc, cache, db, rabbit, _ = make_service(order=order)
    await svc.handle_payment_success({"user_id": 1, "order_id": 9})
    assert order.status == OrderStatus.PROCESSING
    assert order.is_paid is True and order.paid_at is not None
    assert cache.deleted, "cart cache key should be evicted"
    await asyncio.sleep(0)  # let the fire-and-forget analytics task run
    await asyncio.sleep(0)
    assert any(rk == "airdeliver.ai.analytics.conversion" for rk, _ in rabbit.events)


@pytest.mark.asyncio
async def test_payment_success_is_idempotent_for_non_pending_order():
    order = Order(id=9, user_id=1, status=OrderStatus.PROCESSING, total_price=21.0, is_paid=True)
    svc, cache, db, rabbit, _ = make_service(order=order)
    await svc.handle_payment_success({"user_id": 1, "order_id": 9})
    assert db.commits == 0, "duplicate success event must not re-commit"


@pytest.mark.asyncio
async def test_payment_success_phantom_order_is_ignored():
    svc, cache, db, rabbit, _ = make_service(order=None)
    await svc.handle_payment_success({"user_id": 1, "order_id": 999})
    assert db.commits == 0


@pytest.mark.asyncio
async def test_cancel_order_cancels_pending_and_clears_cart():
    order = Order(id=5, user_id=1, status=OrderStatus.PENDING, total_price=10.0)
    svc, cache, db, rabbit, _ = make_service(order=order)
    await svc.handle_cancel_order({"user_id": 1, "order_id": 5})
    assert order.status == OrderStatus.CANCELLED
    assert cache.deleted


@pytest.mark.asyncio
async def test_cancel_order_rejects_other_users_order():
    order = Order(id=5, user_id=2, status=OrderStatus.PENDING, total_price=10.0)
    svc, cache, db, rabbit, _ = make_service(order=order)
    await svc.handle_cancel_order({"user_id": 1, "order_id": 5})
    assert order.status == OrderStatus.PENDING, "IDOR: another user's order must not change"


@pytest.mark.asyncio
async def test_cancel_order_refuses_in_progress_order():
    order = Order(id=5, user_id=1, status=OrderStatus.PROCESSING, total_price=10.0)
    svc, cache, db, rabbit, _ = make_service(order=order)
    await svc.handle_cancel_order({"user_id": 1, "order_id": 5})
    assert order.status == OrderStatus.PROCESSING
    errors = [p for _, p in cache.published if p.get("type") == "error"]
    assert errors
