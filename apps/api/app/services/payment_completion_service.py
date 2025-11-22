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
        result = await self.db.exec(statement)
        order = result.one_or_none()

        if not order:
            logger.error(f"Order {order_id} not found during payment finalization.")
            return

        if order.status in [OrderStatus.PROCESSING, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED]:
            return

        try:
            order.status = OrderStatus.PROCESSING
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Payment confirmed! 🚀 Your drone is being assigned.",
                    "type": "success_text"
                },
                "airdeliver.ai.response.out"
            )

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": {
                        "order_id": order.id,
                        "status": "PAID",
                        "estimated_delivery": "15 mins"
                    },
                    "type": "ORDER_CONFIRMED"
                },
                "airdeliver.ai.response.out"
            )

            await self.rabbitmq.publish(
                {
                    "order_id": order.id,
                    "user_id": user_id,
                    "location": {
                        "address": order.delivery_address,
                        "lat": order.delivery_lat,
                        "lon": order.delivery_lon
                    },
                    "transaction_id": transaction_id,
                    "priority": "HIGH"
                },
                "airdeliver.logistics.mission.create"
            )

        except Exception as e:
            await self.db.rollback()
            logger.critical(f"Database error during payment finalization for Order {order_id}: {e}")
            raise e
