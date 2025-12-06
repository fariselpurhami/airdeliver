# apps/api/app/services/ai_checkout_service.py

import random
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

        # TRANSACTION SAFETY: Create Order Record FIRST (PENDING)
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
            # IDEMPOTENCY KEY: Ensures no double charge
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
            # [FIXED] Added closing parenthesis
            await self.cache.delete(cart_key)

    def _generate_flight_manifest(self, order_id: int, user_address: str) -> dict:
        """
        Calculates the tactical flight path based on drone physics.
        Drone Specs: 150 km/h, 300km Range, 10kg Payload.
        """
        # Simulation of distance logic (In production, use Google Maps API)
        distance_km = random.uniform(5.0, 25.0)
        speed_kmh = 150.0
        eta_hours = distance_km / speed_kmh
        eta_minutes = int(eta_hours * 60) + 2 # +2 mins for takeoff/landing

        return {
            "mission_id": f"MSN-{order_id}-{random.randint(1000,9999)}",
            "drone_id": f"AIR-X-{random.randint(100,999)}",
            "distance_km": round(distance_km, 1),
            "cruising_altitude": "120m",
            "weather_condition": random.choice(["Clear Sky ☀️", "Light Wind 🍃", "Optimal Visibility 👁️"]),
            "estimated_arrival_mins": eta_minutes,
            "origin": {"lat": 30.0444, "lng": 31.2357, "label": "AirDeliver HQ"}, # Cairo Example
            "destination": {"lat": 30.05, "lng": 31.24, "label": "Drop Zone"}, # Mock User Loc
            "status": "ENGAGING ROTORS"
        }
        # [FIXED] Removed extra parenthesis ')'

    async def handle_payment_success(self, payload: dict):
        """
        Step 2: Activated when payment is CONFIRMED.
        Moves Order from PENDING -> PROCESSING (Triggers Purple UI).
        """
        user_id = payload.get("user_id")
        order_id = payload.get("order_id")

        order = await self.db.get(Order, order_id)
        if not order: return

        if order.status == OrderStatus.PENDING:
            # 1. Update Status (The Purple Switch)
            order.status = OrderStatus.PROCESSING
            order.is_paid = True
            self.db.add(order)
            await self.db.commit()

            flight_data = self._generate_flight_manifest(order.id, order.delivery_address)

            # 2. Notify User (Success Animation)
            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": f"Payment secured! Order #{order.id} is now processing. Drones are engaging rotors... 🚁",
                    "type": "success_text"
                },
                "airdeliver.ai.response.out"
            )

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Uploading flight telemetry...",
                    "type": "FLIGHT_MANIFEST", # New Message Type
                    "flight_data": flight_data
                },
                "airdeliver.ai.response.out"
            )

    async def _handle_failed_payment(self, order: Order, reason: str):
        try:
            order.status = OrderStatus.FAILED
            self.db.add(order)
            await self.db.commit()
            recovery_suggestion = ""
            action_options = ["Retry Payment"]
            
            if "gateway" in reason.lower() or "unreachable" in reason.lower():
                # Technical Fault -> Suggest Alternative Gateway
                recovery_suggestion = "It seems our primary secure tunnel is congested. I recommend switching to PayPal for a faster checkout."
                action_options.append("Switch to PayPal")

            elif "declined" in reason.lower() or "funds" in reason.lower():
                # Financial Fault -> Suggest Save for Later
                recovery_suggestion = "The transaction was declined by the bank. Would you like to save this cart for later?"
                action_options = ["Retry", "Save for Later"]

            else:
                # Unknown Fault
                recovery_suggestion = f"Payment interruption detected: {reason}. Retrying usually fixes this."

            # 3. Send Smart Recovery Message
            await self.rabbitmq.publish(
                {
                    "user_id": order.user_id,
                    "content": recovery_suggestion,
                    "type": "confirmation_prompt", # Reuse prompt UI
                    "options": action_options
                },
                "airdeliver.ai.response.out",
            )

        except Exception as e:
            # [FIXED] Removed extra parenthesis '))' -> ')'
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
                {"user_id": user_id, "content": "Your order has been securely cancelled.", "type": "ORDER_CANCELLED"},
                "airdeliver.ai.response.out",
            )
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": {"items": [], "total": 0.0}, "type": "cart_preview"},
                "airdeliver.ai.response.out",
            )
        else:
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Order cannot be cancelled at this stage.", "type": "ORDER_CANCELLED"},
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
                db=self.db, user_id=user_id, title="Don't miss out!", body="Your saved order is still waiting. Click to restore it now!"
            )
        except Exception as e:
            logger.warning(f"Failed to schedule reminder for order {order_id}: {e}")
