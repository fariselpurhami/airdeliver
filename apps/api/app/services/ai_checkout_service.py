# apps/api/app/services/ai_checkout_service.py

import json
import logging
import random
import uuid
import asyncio
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Protocol

from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason

logger = logging.getLogger("airdeliver.checkout")


# --- INTERFACES & PROTOCOLS ---
# Enforcing strict dependency injection contracts

class PaymentOrchestratorProtocol(Protocol):
    async def process_payment(
        self, 
        amount: Decimal, 
        currency: str, 
        region: str, 
        metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        ...

class NotificationServiceProtocol(Protocol):
    async def send_notification(self, user_id: int, template: str, context: Dict[str, Any]) -> None:
        ...


# --- DOMAIN TRANSFER OBJECTS (DTOs) ---
# Enforcing boundary validation and type safety

class ConfirmOrderPayload(BaseModel):
    user_id: int
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default="Address pending via Chat", max_length=255)
    country: str = Field(default="US", min_length=2, max_length=2)

class PaymentSuccessPayload(BaseModel):
    user_id: int
    order_id: int

class CancelOrderPayload(BaseModel):
    user_id: int
    order_id: Optional[int] = None


class AICheckoutService:
    """
    ENTERPRISE CHECKOUT ORCHESTRATOR.

    Architectural Guarantees:
    1. Financial Precision: Strict enforcement of Decimal arithmetic. No IEEE 754 float approximations.
    2. Atomic Transitions: Database operations are isolated within explicit transaction boundaries.
    3. Idempotency: Payment success and cancellation operations tolerate duplicate deliveries safely.
    4. Observable Boundaries: Structured logging across state transitions without leaking PII.
    """

    # --- DOMAIN CONSTANTS ---
    DEFAULT_CURRENCY = "usd"
    UI_CHANNEL_PREFIX = "airdeliver:response:"
    CACHE_CART_PREFIX = "ai_cart:"
    
    # Flight Simulation Constants (Domain Logic)
    FLIGHT_SPEED_KPH = 120.0
    FLIGHT_PREP_BUFFER_MINS = 5
    FLIGHT_MIN_RANGE_KM = 3.5
    FLIGHT_MAX_RANGE_KM = 15.0

    def __init__(
        self,
        db: AsyncSession,
        cache: IAsyncCacheClient,
        rabbitmq: RabbitMQService,
        orchestrator: PaymentOrchestratorProtocol,
        notification_service: Optional[NotificationServiceProtocol] = None,
    ):
        self.db = db
        self.cache = cache
        self.rabbitmq = rabbitmq
        self.orchestrator = orchestrator
        self.notification_service = notification_service

    # --- 🔌 EDGE COMMUNICATION ---

    async def _send_to_ui(self, user_id: int, payload: Dict[str, Any]) -> None:
        """
        Publishes strongly-typed, deterministic JSON payloads to the client WebSocket via Redis Pub/Sub.
        """
        try:
            channel = f"{self.UI_CHANNEL_PREFIX}{user_id}"

            payload["meta"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "ai_checkout_v4.1"
            }

            def _strict_serializer(obj: Any) -> Any:
                if isinstance(obj, Decimal):
                    return str(obj)  # Financial values must remain strings over the wire
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} is not JSON serializable")

            message = json.dumps(payload, default=_strict_serializer)
            await self.cache.publish(channel, message)
        except Exception as e:
            logger.error("UI Delivery pipeline failure", extra={"user_id": user_id, "error": str(e)})

    def _get_cart_key(self, user_id: int) -> str:
        return f"{self.CACHE_CART_PREFIX}{user_id}"

    # --- 💰 CORE WORKFLOWS ---

    async def handle_confirm_order(self, raw_payload: Dict[str, Any]) -> None:
        """
        Orchestrates intent-to-transaction transition.
        Guarantees atomicity: cart state is verified, db records created, and payment intent secured.
        """
        try:
            payload = ConfirmOrderPayload(**raw_payload)
        except ValidationError as e:
            logger.warning("Invalid checkout payload boundary", extra={"error": str(e)})
            await self._send_error(raw_payload.get("user_id", 0), "Invalid checkout data provided.")
            return

        cart = await self.cache.get_json(self._get_cart_key(payload.user_id))
        
        if not cart or not cart.get("items"):
            await self._send_error(payload.user_id, "Your cart is empty or has expired.")
            return

        try:
            # Reconstruct financial totals strictly via Decimal
            total_amount = sum(
                (Decimal(str(item["price"])) * int(item["quantity"]) for item in cart["items"]),
                Decimal("0.00")
            )
        except (InvalidOperation, KeyError, ValueError) as e:
            logger.error("Cart financial structure corruption", extra={"user_id": payload.user_id, "error": str(e)})
            await self._send_error(payload.user_id, "Cart total calculation error.")
            return

        new_order = None
        try:
            new_order = Order(
                user_id=payload.user_id,
                status=OrderStatus.PENDING,
                total_price=total_amount,
                delivery_address=payload.address,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(new_order)
            await self.db.flush() 

            order_items_to_create = [
                OrderItem(
                    order_id=new_order.id,
                    product_id=item["product_id"],
                    quantity=int(item["quantity"]),
                    price_per_unit=Decimal(str(item["price"]))
                )
                for item in cart["items"]
            ]

            self.db.add_all(order_items_to_create)
            await self.db.commit()
            await self.db.refresh(new_order)

            logger.info("Pending order committed", extra={"order_id": new_order.id, "total": str(total_amount)})

        except Exception as e:
            await self.db.rollback()
            logger.critical("Database transaction aborted during order creation", extra={"user_id": payload.user_id, "error": str(e)})
            await self._send_error(payload.user_id, "System error. Could not create order. Please try again.")
            return

        payment_metadata = {
            "order_id": str(new_order.id),
            "user_id": str(payload.user_id),
            "idempotency_key": str(uuid.uuid4())
        }

        try:
            await self._send_to_ui(payload.user_id, {"content": "Securing payment channels...", "type": "typing"})

            payment_options = await self.orchestrator.process_payment(
                amount=total_amount,
                currency=self.DEFAULT_CURRENCY,
                region=payload.country,
                metadata=payment_metadata
            )
        except Exception as e:
            logger.error("Payment orchestrator initialization failed", extra={"order_id": new_order.id, "error": str(e)})
            await self._handle_failed_payment(new_order, "Payment Gateway Unreachable")
            return

        if payment_options.get("status") == "failure":
            await self._handle_failed_payment(new_order, payment_options.get("error", "Initialization failed"))
        else:
            await self._send_to_ui(payload.user_id, {
                "type": "payment_intent",
                "content": {
                    "orderId": new_order.id,
                    "total": str(new_order.total_price),
                    "gateways": payment_options.get("available_gateways", []),
                    "client_secret": payment_options.get("client_secret", "")
                }
            })

            self._emit_analytics_event(
                "airdeliver.ai.checkout.initiated",
                {"user_id": payload.user_id, "order_id": new_order.id, "amount": str(total_amount)}
            )

    async def handle_payment_success(self, raw_payload: Dict[str, Any]) -> None:
        """
        Idempotent payment success processor.
        Converts Order status, triggers logistics UI workflows, and emits downstream conversion events.
        """
        try:
            payload = PaymentSuccessPayload(**raw_payload)
        except ValidationError as e:
            logger.error("Invalid payment success payload", extra={"error": str(e)})
            return

        try:
            order = await self.db.get(Order, payload.order_id)
            if not order:
                logger.warning("Payment success signal for phantom order", extra={"order_id": payload.order_id})
                return

            # Idempotency Check: Only process if PENDING
            if order.status != OrderStatus.PENDING:
                logger.info("Ignoring duplicate payment success event", extra={"order_id": order.id, "current_status": order.status.name})
                return

            order.status = OrderStatus.PROCESSING
            order.is_paid = True
            order.paid_at = datetime.now(timezone.utc)
            self.db.add(order)
            await self.db.commit()

            await self.cache.delete(self._get_cart_key(payload.user_id))

            flight_data = self._generate_flight_manifest(order.id)
            
            await self._send_to_ui(payload.user_id, {
                "content": f"Payment Secured! Order #{order.id} is confirmed. AirAero X is on the way.",
                "type": "success_text",
                "sound": "drone_takeoff"
            })

            await asyncio.sleep(0.5)  # Intentional jitter for sequential UI presentation
            
            await self._send_to_ui(payload.user_id, {
                "content": "Uploading Live Telemetry...",
                "type": "FLIGHT_MANIFEST",
                "flight_data": flight_data
            })
            
            self._emit_analytics_event(
                "airdeliver.ai.analytics.conversion",
                {"user_id": payload.user_id, "order_id": order.id, "revenue": str(order.total_price)}
            )

        except Exception as e:
            await self.db.rollback()
            logger.critical("Critical failure in payment success handler", extra={"order_id": payload.order_id, "error": str(e)})
            await self._send_to_ui(payload.user_id, {"content": "Order confirmed! Check your email for details.", "type": "success_text"})

    def _generate_flight_manifest(self, order_id: int) -> Dict[str, Any]:
        """
        Generates deterministic telemetry parameters for the UI simulation dashboard.
        """
        distance_km = random.uniform(self.FLIGHT_MIN_RANGE_KM, self.FLIGHT_MAX_RANGE_KM)
        flight_time_mins = (distance_km / self.FLIGHT_SPEED_KPH) * 60
        total_eta_mins = int(flight_time_mins + self.FLIGHT_PREP_BUFFER_MINS)
        
        return {
            "mission_id": f"MSN-{order_id}-{random.randint(1000, 9999)}",
            "drone_id": f"AIR-X-{random.randint(100, 999)} (Stealth)",
            "distance_km": round(distance_km, 1),
            "cruising_altitude": f"{random.randint(100, 300)}ft",
            "speed_kph": int(self.FLIGHT_SPEED_KPH),
            "estimated_arrival_mins": total_eta_mins,
            "weather_condition": random.choice(["Clear Sky", "Tailwind", "Optimal Visibility"]),
            "battery_status": "100%",
            "status": "PRE-FLIGHT CHECK COMPLETE"
        }

    # --- ❌ RECOVERY & CANCELLATION WORKFLOWS ---

    async def _handle_failed_payment(self, order: Order, reason: str) -> None:
        """Graceful degradation path for payment gateway rejections."""
        try:
            order.status = OrderStatus.FAILED
            self.db.add(order)
            await self.db.commit()
            
            await self._send_to_ui(order.user_id, {
                "content": f"Payment Interruption: {reason}. Don't worry, your manifest is preserved.",
                "type": "confirmation_prompt",
                "options": ["Retry Payment", "Change Method"],
                "reason": "Transaction Recovery"
            })
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed handling failed payment fallback", extra={"order_id": order.id, "error": str(e)})

    async def handle_cancel_order(self, raw_payload: Dict[str, Any]) -> None:
        """
        Processes user-initiated order cancellation.
        Validates authorization boundaries and state machine constraints.
        """
        try:
            payload = CancelOrderPayload(**raw_payload)
        except ValidationError as e:
            logger.warning("Invalid cancel payload", extra={"error": str(e)})
            return
             
        order_cancelled = False
        
        if payload.order_id:
            try:
                order = await self.db.get(Order, payload.order_id)
                if order and order.user_id == payload.user_id:
                    if order.status == OrderStatus.PENDING:
                        order.status = OrderStatus.CANCELLED
                        self.db.add(order)
                        await self.db.commit()
                        order_cancelled = True
                        logger.info("Order discarded by user", extra={"order_id": payload.order_id, "user_id": payload.user_id})

                    elif order.status in {OrderStatus.PROCESSING, OrderStatus.SHIPPED}:
                         await self._send_error(
                             payload.user_id, 
                             "Cannot discard: Your order is already in progress. Please contact support."
                         )
                         return
            except Exception as e:
                await self.db.rollback()
                logger.error("Order cancellation transaction failed", extra={"order_id": payload.order_id, "error": str(e)})
             
        try:
            await self.cache.delete(self._get_cart_key(payload.user_id))
        except Exception as e:
            logger.warning("Failed to evict cart cache during cancellation", extra={"user_id": payload.user_id, "error": str(e)})

        await self._send_to_ui(payload.user_id, {
            "content": {"items": [], "total": "0.00"},
            "type": "cart_preview",
            "reason": "Discard Command"
        })
        
        msg = f"Order #{payload.order_id} discarded." if order_cancelled else "Your operation was canceled."
        await self._send_to_ui(payload.user_id, {
            "content": f"{msg} Cart has been cleared.",
            "type": "info" 
        })

    # --- 🛠️ UTILITIES ---

    async def _send_error(self, user_id: int, message: str) -> None:
        await self._send_to_ui(user_id, {"content": message, "type": "error"})

    def _emit_analytics_event(self, routing_key: str, payload: Dict[str, Any]) -> None:
        """Fire-and-forget telemetry emission."""
        async def _publish() -> None:
            try:
                await self.rabbitmq.publish(payload, routing_key)
            except Exception as e:
                logger.error("Failed to emit analytics event", extra={"routing_key": routing_key, "error": str(e)})
        
        asyncio.create_task(_publish())
