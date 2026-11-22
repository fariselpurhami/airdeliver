"""Seam tests: the live Stripe success path must also clear the paid cart and
emit the conversion analytics event (these previously lived only in the
never-invoked AICheckoutService.handle_payment_success)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import OrderStatus
from app.models.order import Order
from app.services.payment_completion_service import PaymentCompletionService


def _service(order):
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.one_or_none.return_value = order
    db.execute = AsyncMock(return_value=result)
    rabbitmq = AsyncMock()
    cache = AsyncMock()
    return PaymentCompletionService(db, rabbitmq, cache), db, rabbitmq, cache


def _order(status=OrderStatus.PENDING, total=42.5):
    return Order(id=7, user_id=99, status=status, total_price=total)


@pytest.mark.asyncio
async def test_success_clears_cart_and_emits_conversion():
    svc, _, rabbitmq, cache = _service(_order())
    await svc.finalize_successful_payment(order_id=7, user_id=99, transaction_id="pi_1")

    cache.delete.assert_awaited_once_with("ai_cart:99")
    routing_keys = [c.args[1] for c in rabbitmq.publish.await_args_list]
    assert "airdeliver.ai.analytics.conversion" in routing_keys
    conv = [c.args[0] for c in rabbitmq.publish.await_args_list if c.args[1] == "airdeliver.ai.analytics.conversion"][0]
    assert conv["user_id"] == 99
    assert conv["order_id"] == 7
    assert float(conv["revenue"]) == 42.5


@pytest.mark.asyncio
async def test_success_without_cache_still_emits_conversion():
    svc, _, rabbitmq, _ = _service(_order())
    svc.cache = None
    await svc.finalize_successful_payment(order_id=7, user_id=99, transaction_id="pi_1")
    routing_keys = [c.args[1] for c in rabbitmq.publish.await_args_list]
    assert "airdeliver.ai.analytics.conversion" in routing_keys


@pytest.mark.asyncio
async def test_already_paid_order_is_idempotent_noop():
    svc, _, rabbitmq, cache = _service(_order(status=OrderStatus.PROCESSING))
    await svc.finalize_successful_payment(order_id=7, user_id=99, transaction_id="pi_1")
    rabbitmq.publish.assert_not_awaited()
    cache.delete.assert_not_awaited()
