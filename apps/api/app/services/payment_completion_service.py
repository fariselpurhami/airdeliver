# apps/api/app/services/payment_completion_service.py

import logging
from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.rabbitmq_service import RabbitMQService
from app.services.gamification_service import gamification_service
from app.services.cache_service import IAsyncCacheClient

logger = logging.getLogger(__name__)

class PaymentCompletionService:
    CART_KEY_PREFIX = "ai_cart:"

    def __init__(self, db: AsyncSession, rabbitmq: RabbitMQService, cache: Optional[IAsyncCacheClient] = None):
        self.db = db
        self.rabbitmq = rabbitmq
        self.cache = cache

    async def finalize_successful_payment(self, order_id: int, user_id: int, transaction_id: str):
        statement = select(Order).where(Order.id == order_id).with_for_update()
        result = await self.db.execute(statement)
        order = result.one_or_none()

        if not order:
            logger.error(f"Order {order_id} not found during payment finalization.")
            return

        if order.status in [OrderStatus.PROCESSING, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
            return

        try:
            order.status = OrderStatus.PROCESSING
            order.payment_transaction_id = transaction_id
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Payment confirmed! 🚀 Your order is being prepared for delivery.",
                    "type": "success_text"
                },
                "airdeliver.ai.response.out"
            )

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": {
                        "order_id": order.id,
                        "status": "PAID"
                    },
                    "type": "ORDER_CONFIRMED"
                },
                "airdeliver.ai.response.out"
            )

            # Post-payment side effects that previously lived only in the
            # never-invoked AICheckoutService.handle_payment_success:
            # 1. Clear the paid cart so the user does not see it as still active.
            if self.cache is not None:
                try:
                    await self.cache.delete(f"{self.CART_KEY_PREFIX}{user_id}")
                except Exception as exc:
                    logger.warning("cart cleanup after payment failed", extra={"user_id": user_id, "error": str(exc)})

            # 2. Award gamification points/badges for the paid order
            #    (best-effort: never blocks or fails payment finalization).
            try:
                await gamification_service.award_points_for_purchase(
                    self.db, user_id, float(order.total_price or 0)
                )
            except Exception as exc:
                logger.warning("gamification award failed", extra={"order_id": order_id, "error": str(exc)})

            # 3. Emit the conversion analytics event (consumed by the worker
            #    into the BehaviorEngine as the strongest buy signal).
            try:
                await self.rabbitmq.publish(
                    {
                        "user_id": user_id,
                        "order_id": order.id,
                        "revenue": str(order.total_price),
                    },
                    "airdeliver.ai.analytics.conversion",
                )
            except Exception as exc:
                logger.warning("conversion event emission failed", extra={"order_id": order_id, "error": str(exc)})

        except Exception as e:
            await self.db.rollback()
            logger.critical(f"Database error during payment finalization for Order {order_id}: {e}")
            raise e
