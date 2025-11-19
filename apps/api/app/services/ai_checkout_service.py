# apps/api/app/services/ai_checkout_service.py

from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.services.payment_orchestrator import PaymentOrchestrator
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason
from sqlmodel.ext.asyncio.session import AsyncSession
from decimal import Decimal
from app.services.notification_service import NotificationService
from app.models.user import User
import uuid

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
        user_id = payload["user_id"]
        cart_key = self._get_cart_key(user_id)
        cart = await self.cache.get_json(cart_key)

        if not cart or not cart["items"]:
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Your cart is empty.", "type": "error"},
                "airdeliver.ai.response.out",
            )
            return

        total = Decimal(str(cart["total"]))
        delivery_addr = payload.get("address", "Default Address")

        new_order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_price=float(total),
            delivery_address=delivery_addr,
        )
        self.db.add(new_order)

        order_items_to_create = [
            OrderItem(
                product_id=item["product_id"],
                quantity=item["quantity"],
                price_per_unit=item["price"],
                order=new_order
            ) for item in cart["items"]
        ]
        self.db.add_all(order_items_to_create)

        await self.db.commit()
        await self.db.refresh(new_order)

        payment_metadata = {
            "order_id": str(new_order.id),
            "user_id": str(user_id),
            "user_email": payload.get("email"),
            "phone_number": payload.get("phone"),
        }

        payment_options = await self.orchestrator.process_payment(
            amount=float(total),
            currency="usd",
            region=payload.get("country", "US"),
            metadata=payment_metadata
        )

        if payment_options.get("status") == "failure":
            new_order.status = OrderStatus.FAILED
            self.db.add(new_order)
            await self.db.commit()
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": payment_options.get("error", "Payment failed"), "type": "error"},
                "airdeliver.ai.response.out",
            )
        else:
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

    async def handle_cancel_order(self, payload: dict):
        order = await self.db.get(Order, payload["order_id"])
        if order and order.user_id == payload["user_id"] and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            self.db.add(order)
            await self.db.commit()
            await self.rabbitmq.publish(
                {
                    "user_id": payload["user_id"],
                    "content": "Order successfully cancelled.",
                    "type": "ORDER_CANCELLED"
                },
                "airdeliver.ai.response.out",
            )
        else:
            await self.rabbitmq.publish(
                {
                    "user_id": payload["user_id"],
                    "content": "Order could not be cancelled.",
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
            await self.db.refresh(order)

            await self._schedule_smart_reminder(order.id, order.recovery_token, order.user_id)

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Order saved to wishlist. We will remind you later!", "type": "success_text"},
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
        else:
             await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Error: Order not found or already processed.", "type": "ORDER_CANCELLED"},
                "airdeliver.ai.response.out",
            )

    async def _schedule_smart_reminder(self, order_id: int, token: str, user_id: int):
        user = await self.db.get(User, user_id)
        if not user: return

        await self.notification_service.send_web_push(
            db=self.db,
            user_id=user_id,
            title="Don't miss out!",
            body="Your saved order is still waiting. Click to restore it now!"
        )

        self.notification_service.send_email(
            email_address=user.email,
            subject=f"Restore your order #{order_id}",
            content=f"Your items are ready. Restore using link: /recover/{token}"
        )
