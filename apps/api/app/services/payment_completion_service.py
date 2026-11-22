# apps/api/app/services/payment_completion_service.py

import logging
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.rabbitmq_service import RabbitMQService

logger = logging.getLogger(__name__)

class PaymentCompletionService:
    def __init__(self, db: AsyncSession, rabbitmq: RabbitMQService):
        self.db = db
        self.rabbitmq = rabbitmq

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

        except Exception as e:
            await self.db.rollback()
            logger.critical(f"Database error during payment finalization for Order {order_id}: {e}")
            raise e
