# backend/api/app/services/payment_completion_service.py
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.rabbitmq_service import RabbitMQService
from app.services.gamification_service import gamification_service
from app.services.cache_service import IAsyncCacheClient
from app.services.payment_outbox_service import stage_payment_events, dispatch_pending

logger = logging.getLogger('app.services.payment_completion_service')


class PaymentCompletionService:
    CART_KEY_PREFIX = "ai_cart:"

    def __init__(self, db: AsyncSession, rabbitmq: RabbitMQService, cache: Optional[IAsyncCacheClient] = None):
        self.db = db
        self.rabbitmq = rabbitmq
        self.cache = cache

    async def finalize_successful_payment(self, order_id: int, user_id: int, transaction_id: str):
        result = await self.db.execute(select(Order).where(Order.id == order_id).with_for_update())
        order = result.scalars().one_or_none()
        if not order:
            raise ValueError("Payment order not found")
        if order.user_id != user_id:
            raise ValueError("Payment owner does not match order owner")
        if not transaction_id or len(transaction_id) > 255:
            raise ValueError("Invalid payment transaction identifier")
        if order.payment_transaction_id and order.payment_transaction_id != transaction_id:
            raise ValueError("Payment transaction does not match order")

        already_paid = order.is_paid or order.status in {
            OrderStatus.PROCESSING, OrderStatus.ASSIGNED,
            OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED,
        }
        if already_paid:
            # A retry must not recreate events or rewards, but must recover
            # publication that failed after the original paid-state commit.
            await self.db.commit()
            dispatched = await dispatch_pending(self.db, self.rabbitmq, order_id=order_id)
            if dispatched.failed:
                raise RuntimeError("Payment saved; event delivery will retry")
            return
        if order.status not in {OrderStatus.PENDING, OrderStatus.FAILED}:
            raise ValueError("Order state requires manual payment reconciliation")

        try:
            order.status = OrderStatus.PROCESSING
            order.payment_transaction_id = transaction_id
            if transaction_id.startswith("pi_"):
                order.stripe_payment_id = transaction_id
            order.is_paid = True
            order.paid_at = datetime.now(timezone.utc)
            total_price = float(order.total_price or 0)
            self.db.add(order)
            stage_payment_events(self.db, order)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.error('Payment state/outbox transaction failed', extra={'order_id': order_id})
            raise

        # These existing features are best effort, not covered by the event
        # outbox. Transactional, idempotent reward handling is separate work.
        if self.cache is not None:
            try:
                snapshot = (order.checkout_data or {}).get("cart_snapshot")
                if isinstance(snapshot, dict) and isinstance(snapshot.get("items"), list):
                    removed = await self.cache.compare_json_required(
                        f"{self.CART_KEY_PREFIX}{user_id}", snapshot, None, delete=True)
                    if removed is not True:
                        logger.info("Post-payment cart differs from checkout; preserved", extra={"order_id": order_id})
                else:
                    # Old orders have no reliable cart snapshot. Never guess
                    # that the customer's current cart belongs to this payment.
                    logger.info("Post-payment cart preserved without checkout snapshot", extra={"order_id": order_id})
            except Exception:
                logger.warning("Cart cleanup after payment failed", extra={"user_id": user_id})
        try:
            await gamification_service.award_points_for_purchase(self.db, user_id, total_price)
        except Exception:
            await self.db.rollback()
            logger.warning("Gamification award failed", extra={"order_id": order_id})

        dispatched = await dispatch_pending(self.db, self.rabbitmq, order_id=order_id)
        if dispatched.failed:
            raise RuntimeError("Payment saved; event delivery will retry")
