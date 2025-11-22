# apps/api/app/services/ai_checkout_service.py

import logging
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.services.payment_orchestrator import PaymentOrchestrator
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason
from app.services.notification_service import NotificationService
from app.models.user import User

logger = logging.getLogger(__name__)

class AICheckoutService:
    def __init__(
        self,
        db: AsyncSession,
        cache: IAsyncCacheClient,
        rabbitmq: RabbitMQService,
        orchestrator: PaymentOrchestrator,
        notification_service: NotificationService = NotificationService(),
    ):
        self.db = db
        self.cache = cache
        self.rabbitmq = rabbitmq
        self.orchestrator = orchestrator
        self.notification_service = notification_service

    def _get_cart_key(self, user_id: int) -> str:
        return f"ai_cart:{user_id}"

    async def handle_confirm_order(self, payload: dict):
        user_id = payload.get("user_id")
        if not user_id: return

        cart_key = self._get_cart_key(user_id)
        cart = await self.cache.get_json(cart_key)

        if not cart or not cart.get("items"):
            await self._send_error(user_id, "Your cart is empty.")
            return

        total = Decimal(str(cart.get("total", "0.00")))
        delivery_addr = payload.get("address", "Default Address")

        try:
            new_order = Order(
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_price=float(total),
                delivery_address=delivery_addr,
            )
            self.db.add(new_order)
            await self.db.flush()

            order_items_to_create = [
                OrderItem(
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price_per_unit=item["price"],
                    order_id=new_order.id
                ) for item in cart["items"]
            ]
            self.db.add_all(order_items_to_create)

            await self.db.commit()
            await self.db.refresh(new_order)

        except Exception as e:
            await self.db.rollback()
            logger.critical(f"FATAL: Database Transaction Failed for User {user_id}: {e}", exc_info=True)
            await self._send_error(user_id, "System error creating order record. No charges applied.")
            return

        payment_metadata = {
            "order_id": str(new_order.id),
            "user_id": str(user_id),
            "user_email": payload.get("email"),
            "phone_number": payload.get("phone"),
            "idempotency_key": str(uuid.uuid4())
        }

        try:
            payment_options = await self.orchestrator.process_payment(
                amount=float(total),
                currency="usd",
                region=payload.get("country", "US"),
                metadata=payment_metadata
            )
        except Exception as e:
            logger.error(f"Payment Orchestration Failure for Order {new_order.id}: {e}")
            await self._handle_failed_payment(new_order, "Payment gateway unreachable.")
            return

        if payment_options.get("status") == "failure":
            await self._handle_failed_payment(new_order, payment_options.get("error", "Payment initialization failed"))
        else:
            logger.info(f"Payment Initialized for Order {new_order.id}. Waiting for Client Action.")

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": {
                        "orderId": new_order.id,
                        "total": new_order.total_price,
                        "gateways": payment_options.get("available_gateways", []),
                    },
                    "type": "payment_intent",
                },
                "airdeliver.ai.response.out",
            )
            await self.cache.delete(cart_key)

    async def _handle_failed_payment(self, order: Order, reason: str):
        try:
            order.status = OrderStatus.FAILED
            self.db.add(order)
            await self.db.commit()

            await self._send_error(order.user_id, reason)
        except Exception as e:
            logger.critical(f"Double Fault: Failed to update failed order status {order.id}: {e}")

    async def _send_error(self, user_id: int, message: str):
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": message, "type": "error"},
            "airdeliver.ai.response.out",
        )

    async def handle_cancel_order(self, payload: dict):
        user_id = payload.get("user_id")

        raw_msg = payload.get("message")
        order_id = None

        if isinstance(raw_msg, dict):
             order_id = payload.get("order_id") or raw_msg.get("orderId") or raw_msg.get("order_id")
        else:
             order_id = payload.get("order_id")

        if not order_id:
            logger.warning(f"Cancel attempt failed: Missing order_id. Payload: {payload}")
            return

        order = await self.db.get(Order, int(order_id))

        if order and order.user_id == user_id and order.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            order.status = OrderStatus.CANCELLED
            self.db.add(order)
            await self.db.commit()

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Your order has been securely cancelled.",
                    "type": "ORDER_CANCELLED"
                },
                "airdeliver.ai.response.out",
            )

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": {"items": [], "total": 0.0}, "type": "cart_preview"},
                "airdeliver.ai.response.out",
            )

        else:
            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Order cannot be cancelled at this stage.",
                    "type": "ORDER_CANCELLED"
                },
                "airdeliver.ai.response.out",
            )

    async def handle_save_for_later(self, payload: dict):
        user_id = payload["user_id"]
        order_id = payload.get("order_id")
        reason_val = payload.get("reason", "other")

        try:
            reason = CancellationReason(reason_val)
        except ValueError:
            reason = CancellationReason.OTHER

        order = await self.db.get(Order, order_id)
        if order and order.user_id == user_id:
            order.status = OrderStatus.SAVED_FOR_LATER
            order.cancellation_reason = reason
            order.recovery_token = str(uuid.uuid4())

            self.db.add(order)
            await self.db.commit()

            asyncio.create_task(self._schedule_smart_reminder(order.id, order.recovery_token, user_id))

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Order saved to wishlist. We will remind you later!", "type": "success_text"},
                "airdeliver.ai.response.out",
            )

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": {"items": [], "total": 0.0}, "type": "cart_preview"},
                "airdeliver.ai.response.out",
            )

    async def handle_hard_cancel(self, payload: dict):
        user_id = payload["user_id"]
        order_id = payload.get("order_id")
        reason_val = payload.get("reason", "changed_mind")

        try:
            reason = CancellationReason(reason_val)
        except ValueError:
            reason = CancellationReason.CHANGED_MIND

        order = await self.db.get(Order, order_id)

        if order and order.user_id == user_id:
            order.status = OrderStatus.CANCELLED
            order.cancellation_reason = reason
            self.db.add(order)
            await self.db.commit()

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Order canceled. Want me to suggest cheaper alternatives?", "type": "ORDER_CANCELLED"},
                "airdeliver.ai.response.out",
            )

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": {"items": [], "total": 0.0}, "type": "cart_preview"},
                "airdeliver.ai.response.out",
            )

    async def _schedule_smart_reminder(self, order_id: int, token: str, user_id: int):
        try:
            user = await self.db.get(User, user_id)
            if not user: return

            await self.notification_service.send_web_push(
                db=self.db,
                user_id=user_id,
                title="Don't miss out!",
                body="Your saved order is still waiting. Click to restore it now!"
            )
        except Exception as e:
            logger.warning(f"Failed to schedule reminder for order {order_id}: {e}")
