"""Use real ORM models and SQLAlchemy Row results, not permissive MagicMock orders."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.payment_completion_service import PaymentCompletionService


@pytest.fixture
def payment_service(monkeypatch):
    engine = create_engine("sqlite://")
    Order.__table__.create(engine)
    from app.models.payment_outbox import PaymentOutbox
    PaymentOutbox.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        order = Order(id=7, user_id=99, total_price=42.5)
        session.add(order)
        session.commit()
        db = MagicMock()
        db.execute = AsyncMock(side_effect=session.execute)
        db.commit = AsyncMock(side_effect=session.commit)
        db.refresh = AsyncMock(side_effect=session.refresh)
        db.rollback = AsyncMock(side_effect=session.rollback)
        db.add = session.add
        broker, cache = AsyncMock(), AsyncMock()
        from app.services.rabbitmq_service import PublishOutcome, PublishResult
        broker.publish.return_value = PublishOutcome(PublishResult.CONFIRMED, "test", "test", 1, 1.0)
        from app.services import payment_completion_service as module
        monkeypatch.setattr(module.gamification_service, "award_points_for_purchase", AsyncMock())
        yield PaymentCompletionService(db, broker, cache), order, db, broker, cache
    engine.dispose()


@pytest.mark.asyncio
async def test_real_model_finalization_records_paid_state(payment_service):
    service, order, _, broker, cache = payment_service
    await service.finalize_successful_payment(7, 99, "pi_verified")
    assert order.status == OrderStatus.PROCESSING
    assert order.is_paid is True
    assert order.paid_at is not None
    assert order.payment_transaction_id == "pi_verified"
    assert order.stripe_payment_id == "pi_verified"
    cache.delete.assert_awaited_once_with("ai_cart:99")
    assert len(broker.publish.await_args_list) == 3


@pytest.mark.asyncio
async def test_mismatched_owner_cannot_finalize_order(payment_service):
    service, order, _, broker, cache = payment_service
    with pytest.raises(ValueError, match="owner"):
        await service.finalize_successful_payment(7, 100, "pi_verified")
    assert order.status == OrderStatus.PENDING
    broker.publish.assert_not_awaited()
    cache.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_paid_assigned_order_cannot_regress(payment_service):
    service, order, db, broker, cache = payment_service
    order.status = OrderStatus.ASSIGNED
    order.is_paid = True
    await db.commit()
    await service.finalize_successful_payment(7, 99, "pi_verified")
    assert order.status == OrderStatus.ASSIGNED
    broker.publish.assert_not_awaited()
    cache.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelled_order_not_silently_reopened(payment_service):
    service, order, db, broker, _ = payment_service
    order.status = OrderStatus.CANCELLED
    await db.commit()
    with pytest.raises(ValueError, match="state"):
        await service.finalize_successful_payment(7, 99, "pi_verified")
    assert order.status == OrderStatus.CANCELLED
    broker.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_committed_payment_recovers_notifications_after_broker_outage(payment_service):
    import asyncio
    service, order, db, broker, _ = payment_service
    broker.publish.side_effect = RuntimeError("broker unavailable")
    with pytest.raises(RuntimeError):
        await service.finalize_successful_payment(7, 99, "pi_verified")
    assert order.is_paid is True
    broker.publish.side_effect = None
    await asyncio.sleep(2.1)
    await service.finalize_successful_payment(7, 99, "pi_verified")
    successful_calls = [call for call in broker.publish.await_args_list if call.kwargs.get("message_id")]
    assert len(successful_calls) >= 3, "Paid-state duplicate skipped delivery recovery"
