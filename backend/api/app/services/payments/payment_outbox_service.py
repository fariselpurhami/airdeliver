"""Transactional payment-event outbox. Broker delivery remains at least once."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from sqlmodel import select
from app.models.payment_outbox import PaymentOutbox

logger = logging.getLogger('app.services.payment_outbox_service')


@dataclass
class DispatchResult:
    sent: int = 0
    failed: int = 0


def stage_payment_events(db, order) -> None:
    """Caller commits these rows in the same transaction as the paid state."""
    user_id = str(order.user_id)
    events = [
        ("payment_text", "airdeliver.ai.response.out", {"user_id": user_id, "content": "Payment confirmed! 🚀 Your order is being prepared for delivery.", "type": "success_text"}),
        ("order_confirmed", "airdeliver.ai.response.out", {"user_id": user_id, "content": {"order_id": order.id, "status": "PAID"}, "type": "ORDER_CONFIRMED"}),
        ("conversion", "airdeliver.ai.analytics.conversion", {"user_id": user_id, "order_id": order.id, "revenue": str(order.total_price)}),
    ]
    for kind, routing_key, payload in events:
        row = PaymentOutbox(order_id=order.id, kind=kind, routing_key=routing_key, payload=payload)
        row.payload = {**payload, "event_id": row.id}
        db.add(row)


async def dispatch_pending(db, rabbitmq, *, order_id: Optional[int] = None, limit: int = 20) -> DispatchResult:
    """Lock one row at a time, publish with confirms, then record delivery.

    A crash after broker acceptance but before this commit can resend the same
    event_id/message_id. Consumers must deduplicate or tolerate that replay.
    """
    result = DispatchResult()
    for _ in range(max(0, min(limit, 50))):
        query = select(PaymentOutbox).where(
            PaymentOutbox.delivered_at.is_(None),
            PaymentOutbox.next_attempt_at <= datetime.now(timezone.utc),
        )
        if order_id is not None:
            query = query.where(PaymentOutbox.order_id == order_id)
        query = query.order_by(PaymentOutbox.created_at).limit(1).with_for_update(skip_locked=True)
        row = (await db.execute(query)).scalars().first()
        if row is None:
            await db.rollback()  # Release the empty read transaction.
            break
        try:
            outcome = await asyncio.wait_for(rabbitmq.publish(
                row.payload, row.routing_key, correlation_id=row.id,
                message_id=row.id, max_retries=1,
            ), timeout=6.0)
            if outcome.is_success is not True:
                raise RuntimeError("Broker did not confirm payment event")
        except Exception as exc:
            row.attempts += 1
            row.last_error = type(exc).__name__[:128]
            row.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=min(300, 2 ** min(row.attempts, 9)))
            db.add(row)
            await db.commit()
            logger.warning("payment_outbox_publish_retry", extra={"error_type": row.last_error})
            result.failed += 1
        else:
            row.attempts += 1
            row.delivered_at = datetime.now(timezone.utc)
            row.last_error = None
            db.add(row)
            await db.commit()
            result.sent += 1
    return result
