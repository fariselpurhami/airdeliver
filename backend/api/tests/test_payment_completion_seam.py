"""The live payment path preserves cart cleanup and durable conversion events."""
import pytest
from app.models.enums import OrderStatus
from tests.test_payment_completion_orm import payment_service


@pytest.mark.asyncio
async def test_success_clears_cart_and_emits_conversion(payment_service):
    svc, order, _, rabbitmq, cache = payment_service
    await svc.finalize_successful_payment(7, 99, "pi_1")
    cache.compare_json_required.assert_awaited_once_with("ai_cart:99", order.checkout_data["cart_snapshot"], None, delete=True)
    conversions = [call.args[0] for call in rabbitmq.publish.await_args_list if call.args[1] == "airdeliver.ai.analytics.conversion"]
    assert len(conversions) == 1
    assert conversions[0]["user_id"] == "99"  # Response consumer requires a string.
    assert conversions[0]["order_id"] == 7
    assert float(conversions[0]["revenue"]) == 42.5
    assert conversions[0]["event_id"]


@pytest.mark.asyncio
async def test_success_without_cache_still_emits_conversion(payment_service):
    svc, _, _, rabbitmq, _ = payment_service
    svc.cache = None
    await svc.finalize_successful_payment(7, 99, "pi_1")
    assert "airdeliver.ai.analytics.conversion" in [call.args[1] for call in rabbitmq.publish.await_args_list]


@pytest.mark.asyncio
async def test_already_paid_order_is_idempotent_noop(payment_service):
    svc, order, db, rabbitmq, cache = payment_service
    order.status = OrderStatus.PROCESSING
    await db.commit()
    await svc.finalize_successful_payment(7, 99, "pi_1")
    rabbitmq.publish.assert_not_awaited()
    cache.delete.assert_not_awaited()
