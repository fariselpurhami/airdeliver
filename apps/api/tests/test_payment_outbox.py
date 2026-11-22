"""Real ORM outbox transaction, retry and broker-confirmation contracts."""
import pytest
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from app.models.order import Order
from app.models.enums import OrderStatus
from app.models.payment_outbox import PaymentOutbox
from app.services.payment_outbox_service import dispatch_pending, stage_payment_events
from app.services.rabbitmq_service import PublishOutcome, PublishResult
from tests.test_payment_completion_orm import payment_service


async def rows(db):
    return (await db.execute(select(PaymentOutbox))).scalars().all()


@pytest.mark.asyncio
async def test_paid_state_and_all_events_rollback_together(payment_service):
    service, order, db, broker, _ = payment_service
    db.commit.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.finalize_successful_payment(7, 99, "pi_1")
    assert await rows(db) == []
    persisted = (await db.execute(select(Order).where(Order.id == 7))).scalars().one()
    assert persisted.status == OrderStatus.PENDING
    assert persisted.is_paid is False
    broker.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfirmed_events_remain_pending_with_backoff(payment_service):
    service, _, db, broker, _ = payment_service
    broker.publish.return_value = PublishOutcome(PublishResult.NACKED, "test", "test", 1, 1.0)
    with pytest.raises(RuntimeError, match="delivery will retry"):
        await service.finalize_successful_payment(7, 99, "pi_1")
    pending = await rows(db)
    assert len(pending) == 3
    for event in pending:
        assert event.delivered_at is None
        assert event.attempts == 1
        assert event.last_error == "RuntimeError"
    calls = broker.publish.await_count
    assert (await dispatch_pending(db, broker)).sent == 0
    assert broker.publish.await_count == calls  # Backoff is enforced.


@pytest.mark.asyncio
async def test_confirmed_events_have_stable_ids_and_no_duplicate_publication(payment_service):
    service, _, db, broker, _ = payment_service
    await service.finalize_successful_payment(7, 99, "pi_1")
    events = await rows(db)
    assert len(events) == 3
    assert all(event.delivered_at is not None and event.attempts == 1 for event in events)
    event_ids = {event.id for event in events}
    for call in broker.publish.await_args_list:
        assert call.kwargs["message_id"] in event_ids
        assert call.kwargs["message_id"] == call.kwargs["correlation_id"] == call.args[0]["event_id"]
    await service.finalize_successful_payment(7, 99, "pi_1")
    assert broker.publish.await_count == 3
    assert len(await rows(db)) == 3


@pytest.mark.asyncio
async def test_event_uniqueness_prevents_recreating_same_payment_notifications(payment_service):
    _, order, db, _, _ = payment_service
    stage_payment_events(db, order)
    await db.commit()
    stage_payment_events(db, order)
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
    assert len(await rows(db)) == 3


@pytest.mark.asyncio
async def test_background_dispatch_survives_callback_process_loss(payment_service):
    _, order, db, broker, _ = payment_service
    order.is_paid = True
    order.status = OrderStatus.PROCESSING
    db.add(order)
    stage_payment_events(db, order)
    await db.commit()  # Simulates a crash immediately after this durable commit.
    dispatched = await dispatch_pending(db, broker, limit=2)
    assert dispatched.sent == 2
    assert sum(row.delivered_at is None for row in await rows(db)) == 1
    assert (await dispatch_pending(db, broker)).sent == 1


@pytest.mark.asyncio
async def test_timeout_does_not_mark_event_delivered(payment_service, monkeypatch):
    import app.services.payment_outbox_service as outbox
    _, order, db, broker, _ = payment_service
    stage_payment_events(db, order)
    await db.commit()
    async def timeout(awaitable, timeout):
        awaitable.close()
        raise TimeoutError()
    monkeypatch.setattr(outbox.asyncio, "wait_for", timeout)
    result = await dispatch_pending(db, broker, limit=1)
    assert result.failed == 1
    assert sum(row.delivered_at is not None for row in await rows(db)) == 0
