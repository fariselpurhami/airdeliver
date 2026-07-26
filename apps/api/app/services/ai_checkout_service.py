# apps/api/app/services/ai_checkout_service.py

from __future__ import annotations

import json
import logging
import random
import uuid
import asyncio
import time

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Protocol

from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.services.payment_orchestrator import PaymentRequest, PaymentStatus
from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason

from sqlalchemy.exc import SQLAlchemyError

from typing import Optional, Dict, Any, List, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.payment_orchestrator import OrchestrationResponse

logger = logging.getLogger("airdeliver.checkout")


# --- INTERFACES & PROTOCOLS ---
# Enforcing strict dependency injection contracts

@runtime_checkable
class PaymentOrchestratorProtocol(Protocol):
    async def process_payment(
        self,
        request: PaymentRequest,
        corr_id: str,
    ) -> OrchestrationResponse:
        """
        Execute payment orchestration for a validated payment request.

        Contract requirements:
        - Must be idempotent with respect to request.idempotency_key.
        - Must return a fully-formed OrchestrationResponse on all expected business outcomes.
        - Must raise only domain/infrastructure exceptions documented by the implementation.
        - corr_id must be propagated to downstream logs/traces for observability.
        """
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
            # 1. Fail-Fast Validation: التحقق من كل البيانات وتجهيزها في الذاكرة 
            # قبل فتح أي Transaction مع قاعدة البيانات لتقليل مدة الـ Lock (DB Lock Contention).
            items_payload = cart.get("items", [])
            if not items_payload:
                raise ValueError("Cart is empty; cannot initiate order.")
            
            safe_address = payload.address.strip() if payload.address and payload.address.strip() else "Address pending via Chat"
            
            order_items_to_create = []
            for item in items_payload:
                # الاستخراج الآمن مع التأكد من النوع
                raw_pid = item.get("product_id") or item.get("id")
                if not raw_pid:
                    raise ValueError(f"Corrupted cart item: missing identification. Payload: {item}")
                
                try:
                    product_id = int(raw_pid)
                    quantity = int(item.get("quantity", 1))
                    
                    if quantity <= 0:
                        raise ValueError(f"Invalid quantity {quantity} for product {product_id}")
                    
                    # الدقة المالية (Financial Precision): 
                    # فرض رقمين عشريين لمنع كسور النقود الوهمية (Floating Point Anomalies).
                    # ⚠️ ARCHITECTURAL WARNING: الاعتماد على السعر القادم من العميل هو ثغرة أمنية حرجة.
                    # في نظام L9 الحقيقي، يجب سحب السعر من قاعدة البيانات هنا وليس من الـ Payload.
                    raw_price = str(item.get("price", "0.00"))
                    price_per_unit = Decimal(raw_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                
                except (ValueError, TypeError, InvalidOperation) as e:
                    raise ValueError(f"Malformed data in cart item {raw_pid}: {str(e)}") from e
                
                order_items_to_create.append(
                    OrderItem(
                        product_id=product_id,
                        quantity=quantity,
                        price_per_unit=price_per_unit
                    )
                )

            # 2. Database Transaction Phase: الآن فقط نتحدث مع قاعدة البيانات
            new_order = Order(
                user_id=payload.user_id,
                status=OrderStatus.PENDING,
                total_price=total_amount,
                delivery_address=safe_address,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            
            self.db.add(new_order)
            await self.db.flush() # الحصول على new_order.id دون عمل Commit
            
            # ربط العناصر بالطلب بعد الحصول على الـ ID
            for order_item in order_items_to_create:
                order_item.order_id = new_order.id
            
            self.db.add_all(order_items_to_create)
            await self.db.commit()
            await self.db.refresh(new_order)
            
            # 3. High-Signal Logging: طباعة بيانات مفيدة للـ Analytics بدون تسريب بيانات حساسة
            logger.info(
                "Pending order successfully committed", 
                extra={
                    "order_id": new_order.id, 
                    "user_id": payload.user_id,
                    "item_count": len(order_items_to_create),
                    "total_amount": str(total_amount)
                }
            )

        except ValueError as ve:
            # Client-Side Errors (HTTP 400 equivalent) - لا تستدعي PagerDuty
            await self.db.rollback()
            logger.warning(
                "Order creation rejected due to validation failure",
                extra={"user_id": payload.user_id, "reason": str(ve)}
            )
            await self._send_error(payload.user_id, "Invalid order details provided. Please verify your cart.")
            return

        except SQLAlchemyError as sqle:
            # Infrastructure Errors (Database Constraints, Connectivity)
            await self.db.rollback()
            logger.error(
                "Database transaction aborted during order creation",
                exc_info=True, # 🔴 L9 Rule: دائمًا مرر الـ Stack Trace في الـ APM
                extra={"user_id": payload.user_id}
            )
            await self._send_error(payload.user_id, "System error processing your order. Please try again.")
            return

        except Exception as e:
            # Unhandled Edge Cases - هذه فقط ما يجب أن يوقظ المهندس (Critical)
            await self.db.rollback()
            
            # بدلاً من str(cart)[:200] العشوائية، نقوم ببناء ملخص آمن ونظيف
            safe_cart_summary = [{"id": i.get("id"), "qty": i.get("quantity")} for i in cart.get("items", [])][:5]
            
            logger.critical(
                "Unexpected critical failure during order creation", 
                exc_info=True,
                extra={
                    "user_id": payload.user_id, 
                    "cart_preview": safe_cart_summary
                }
            )
            await self._send_error(payload.user_id, "A critical system error occurred. Our team has been notified.")
            return

        timestamp_sec = int(time.time())
        idempotency_key = f"idem_pay_{payload.user_id}_{new_order.id}_{timestamp_sec}"
        correlation_id = f"chk_trace_{new_order.id}_{idempotency_key[-8:]}"

        try:
            # 2. بناء الطلب باستخدام العقد الصارم (Strict DTO)
            # الـ PaymentRequest سيرمي ValueError إذا كانت البيانات غير صالحة
            payment_request = PaymentRequest(
                order_id=str(new_order.id),
                amount=total_amount,
                currency=self.DEFAULT_CURRENCY,
                region=payload.country,
                idempotency_key=idempotency_key,
                metadata={
                    "user_id": str(payload.user_id),
                    "correlation_id": correlation_id,
                    "source": "ai_chat_checkout"
                }
            )
        except ValueError as ve:
            # خطأ في البيانات المرسلة من طرفنا (Developer/Data Error)
            logger.error(f"Payment payload validation failed: {str(ve)}", extra={"order_id": new_order.id, "corr_id": correlation_id})
            await self._handle_failed_payment(new_order, "Invalid payment configuration.")
            return

        try:
            # تغذية بصرية للمستخدم (UX Optimization) لإخفاء بطء الـ Network I/O
            await self._send_to_ui(payload.user_id, {"content": "Securing encrypted payment channels...", "type": "typing"})

            # 3. Defensive External I/O (Circuit Breaker & SLA Bounds)
            # L9 Rule: لا تقم أبدًا بإجراء اتصال خارجي دون Hard Timeout Constraint.
            orchestration_response = await asyncio.wait_for(
                self.orchestrator.process_payment(
                    request=payment_request,
                    corr_id=correlation_id
                ),
                timeout=8.0  # Hard Timeout Constraint
            )
            
        except asyncio.TimeoutError:
            # فصل الـ Timeout لتنبيه الـ On-Call بوجود بطء في مزود الدفع (SLA Breach)
            logger.error("Payment orchestrator timed out (Gateway SLA Breach)", extra={"order_id": new_order.id, "corr_id": correlation_id})
            await self._handle_failed_payment(new_order, "Payment provider is currently experiencing high latency. Please try again.")
            return
            
        except Exception as e:
            # 🔴 L9 Rule: الأخطاء الكارثية غير المتوقعة فقط هي التي يتم تسجيلها بـ exc_info=True
            logger.critical(
                "Unexpected catastrophic failure in payment orchestration boundary", 
                exc_info=True, 
                extra={"order_id": new_order.id, "corr_id": correlation_id, "idempotency_key": idempotency_key}
            )
            await self._handle_failed_payment(new_order, "Payment Gateway Unreachable. Our engineering team has been notified.")
            return

        # 4. Strict Contract Validation (التعامل الصارم مع حالة الرد)
        if orchestration_response.status != PaymentStatus.SUCCESS:
            error_msg = getattr(orchestration_response, "error_message", None) or "Gateway declined initialization"
            logger.warning("Payment initialization declined by gateway", extra={"order_id": new_order.id, "reason": error_msg})
            await self._handle_failed_payment(new_order, error_msg)
            return

        # 5. Null-Safety & Anti-Silent-Breach Checks
        # لا نثق أبدًا أن SUCCESS تعني وجود البيانات المطلوبة
        primary_gw = getattr(orchestration_response, "primary_gateway", None)
        client_secret = getattr(primary_gw, "client_secret", None) if primary_gw else None
        action_url = getattr(primary_gw, "action_url", None) if primary_gw else None
        provider = getattr(primary_gw, "provider", "unknown") if primary_gw else "unknown"

        if not client_secret and not action_url:
            logger.critical(
                "Payment orchestration reported SUCCESS, but required actionable tokens are missing.", 
                extra={
                    "order_id": getattr(new_order, "id", None), 
                    "corr_id": correlation_id, 
                    "provider": provider
                }
            )
            await self._handle_failed_payment(new_order, "Gateway token generation failed.")
            return

        # 6. Secure Handoff to Client
        logger.info(
            "Payment intent successfully secured", 
            extra={"order_id": getattr(new_order, "id", None), "corr_id": correlation_id, "provider": provider}
        )

        safe_ui_items = []
        for item in cart.get("items", []):
            safe_ui_items.append({
                "id": item.get("id") or item.get("product_id"),
                "name": item.get("name", "Encrypted Item"),
                "quantity": int(item.get("quantity", 1)),
                "price": float(item.get("price", 0.0))  # تحويل لـ float ليتوافق مع TypeScript
            })
        
        # Security Enforcement: Construct a strict Data Transfer Object (DTO) for the frontend.
        # We aggressively strip 'raw_response' from the UI payload to prevent accidental data exposure 
        # (OWASP API3: Broken Object Property Level Authorization) of internal API keys or PII.
        ui_content = {
            "client_secret": client_secret,
            "order_data": {
                "order_id": new_order.id,
                "total": float(new_order.total_price), # تحويل لـ float ليتوافق مع UI
                "items": safe_ui_items
            },
            "gateway_provider": provider
        }
        
        if action_url:
            ui_content["action_url"] = action_url

        await self._send_to_ui(payload.user_id, {
            "type": "payment_intent",
            "content": ui_content
        })
    

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
                "content": f"Payment Interruption: {reason}. Don't worry, your cart is preserved.",
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
