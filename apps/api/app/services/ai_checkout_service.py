# apps/api/app/services/ai_checkout_service.py

from __future__ import annotations

import json
import logging
import uuid
import asyncio
import time
from hashlib import sha256

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Protocol, Literal

from pydantic import AliasChoices, BaseModel, EmailStr, Field, ValidationError, field_validator
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.services.payment_orchestrator import PaymentRequest, PaymentStatus
from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.models.order import Order, OrderItem
from app.schemas.shipping import ShippingAddress
from app.models.product import Product
from app.models.enums import OrderStatus, CancellationReason

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

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

class ValidatedCheckoutItem(BaseModel):
    product_id: int = Field(ge=1, le=9223372036854775807, strict=True, validation_alias=AliasChoices("product_id", "id"))
    quantity: int = Field(gt=0, le=99, strict=True)
    price: Decimal = Field(ge=0, allow_inf_nan=False, max_digits=10, decimal_places=2)

    @field_validator("product_id", "quantity", mode="before")
    @classmethod
    def reject_booleans(cls, value):
        if isinstance(value, bool):
            raise ValueError("Boolean identifiers/quantities are invalid")
        return value


class ConfirmOrderPayload(BaseModel):
    checkout_request_id: uuid.UUID
    user_id: int
    email: Optional[EmailStr] = None
    shipping_address: ShippingAddress
    payment_provider: Optional[Literal["stripe", "paypal"]] = None
    address: Optional[str] = Field(default=None, max_length=255)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)

class PaymentSuccessPayload(BaseModel):
    user_id: int
    order_id: int

class CancelOrderPayload(BaseModel):
    user_id: int
    order_id: Optional[int] = None


class AICheckoutService:
    """Coordinate checkout through a durable request journal and provider handoff.

    Catalog totals use Decimal arithmetic. The order and frozen provider request
    commit before provider I/O, which is deliberately outside the transaction.
    A request key and fenced setup lease let retries reuse that operation.
    Stock is checked here, not reserved. Legacy finalization is separate.
    """

    # --- DOMAIN CONSTANTS ---
    DEFAULT_CURRENCY = "usd"
    UI_CHANNEL_PREFIX = "airdeliver:response:"
    CACHE_CART_PREFIX = "ai_cart:"
    

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
        """Create or resume an owner-bound, journaled checkout request.

        Provider setup is a separate, retryable operation, not an atomic
        transaction spanning our database and the external provider.
        """
        try:
            payload = ConfirmOrderPayload(**raw_payload)
        except ValidationError as e:
            logger.warning("Invalid checkout payload boundary", extra={"error_count": e.error_count()})
            await self._send_error(raw_payload.get("user_id", 0), "Invalid checkout data provided.")
            return

        fingerprint = sha256(json.dumps(payload.model_dump(mode="json", include={"shipping_address", "payment_provider"}),
                                        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        existing = await self._find_checkout(payload.user_id, str(payload.checkout_request_id))
        if existing is not None:
            return await self._resume_checkout(existing, fingerprint)
        available = [name for name in ("stripe", "paypal") if name in self.orchestrator.available_providers]
        selected_provider = payload.payment_provider or (available[0] if available else None)
        if selected_provider is None:
            await self._send_error(payload.user_id, "Payment is unavailable. Please try again later.")
            return {"status": "rejected"}
        if payload.payment_provider and payload.payment_provider not in self.orchestrator.available_providers:
            await self._send_error(payload.user_id, "The selected payment method is unavailable. Please choose another method.")
            return
        try:
            cart = await self.cache.get_json_required(self._get_cart_key(payload.user_id))
        except Exception as exc:
            logger.warning("Required checkout cart read failed", extra={"error_type": type(exc).__name__})
            await self._send_error(payload.user_id, "Your cart could not be loaded. Refresh before starting checkout again.")
            return {"status": "unconfirmed"}
        # Preserve the exact pre-validation snapshot for atomic price refresh.
        original_cart = json.loads(json.dumps(cart))
        
        if not isinstance(cart, dict) or not isinstance(cart.get("items"), list) or not cart["items"]:
            await self._send_error(payload.user_id, "Your cart is empty or has expired.")
            return

        try:
            if len(cart["items"]) > 100:
                raise ValueError("Cart exceeds the line-item limit")
            validated = [ValidatedCheckoutItem.model_validate(item) for item in cart["items"]]
            counts = {}
            for item in validated:
                counts[item.product_id] = counts.get(item.product_id, 0) + item.quantity
                if counts[item.product_id] > 99:
                    raise ValueError("Product quantity exceeds the checkout limit")
            cart = dict(cart, items=[dict(original, **item.model_dump(mode="json"))
                                    for original, item in zip(cart["items"], validated)])
        except (ValidationError, TypeError, ValueError):
            await self._send_error(payload.user_id, "Invalid cart data. Please review your items and quantities.")
            return

        new_order = None
        try:
            # 1. Fail-Fast Validation: التحقق من كل البيانات وتجهيزها في الذاكرة 
            # قبل فتح أي Transaction مع قاعدة البيانات لتقليل مدة الـ Lock (DB Lock Contention).
            items_payload = cart.get("items", [])
            if not items_payload:
                raise ValueError("Cart is empty; cannot initiate order.")
            
            safe_address = payload.shipping_address.display_address()
            
            order_items_to_create = []
            verified_items = []
            prices_changed = False
            total_amount = Decimal("0.00")
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
                    # Catalog facts are authoritative; the cart price is used
                    # only to detect a change requiring another user review.
                    raw_price = str(item.get("price", "0.00"))
                    cart_price = Decimal(raw_price)
                    product = await self.db.get(Product, product_id, with_for_update=True)
                    if product is None or not product.is_active or product.inventory < counts[product_id]:
                        raise ValueError("Product is unavailable or no longer has sufficient stock")
                    if product.currency.upper() != self.DEFAULT_CURRENCY.upper():
                        raise ValueError("Product currency does not match checkout currency")
                    price_per_unit = Decimal(str(product.price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                    if not price_per_unit.is_finite() or price_per_unit < 0:
                        raise ValueError("Product has an invalid catalog price")
                    prices_changed = prices_changed or cart_price != price_per_unit
                    total_amount += price_per_unit * quantity
                    verified_items.append({**item, "name": product.name, "price": str(price_per_unit)})
                
                except (ValueError, TypeError, InvalidOperation) as e:
                    raise ValueError(f"Malformed data in cart item {raw_pid}: {str(e)}") from e
                
                order_items_to_create.append(
                    OrderItem(
                        product_id=product_id,
                        quantity=quantity,
                        price_per_unit=price_per_unit
                    )
                )

            cart["items"] = verified_items
            cart["total"] = str(total_amount)
            if prices_changed:
                # Release catalog locks before cache/UI I/O. A changed price
                # needs a fresh user review, never an automatic higher charge.
                await self.db.rollback()
                cart["updated_at"] = datetime.now(timezone.utc).isoformat()
                try:
                    confirmed = await self.cache.compare_json_required(
                        self._get_cart_key(payload.user_id), original_cart, cart, ttl=86400)
                except Exception as exc:
                    logger.warning("Checkout price refresh unconfirmed", extra={"error_type": type(exc).__name__})
                    confirmed = False
                if not confirmed:
                    await self._send_error(payload.user_id, "Your cart changed or its refresh could not be confirmed. Refresh your cart before confirming payment.")
                    return {"status": "refresh_required"}
                await self._send_to_ui(payload.user_id, {"type": "cart_preview", "content": cart, "reason": "Catalog Price Update"})
                await self._send_error(payload.user_id, "Prices changed. Please review your refreshed cart before confirming payment.")
                return {"status": "review_required", "cart": cart,
                        "message": "Prices changed. Review the refreshed cart before confirming again."}
            if total_amount <= 0:
                raise ValueError("Checkout total must be positive")

            # 2. Database Transaction Phase: الآن فقط نتحدث مع قاعدة البيانات
            new_order = Order(
                user_id=payload.user_id,
                status=OrderStatus.PENDING,
                total_price=total_amount,
                delivery_address=safe_address,
                currency=self.DEFAULT_CURRENCY.upper(),
                shipping_address_data=payload.shipping_address.model_dump(),
                checkout_request_id=str(payload.checkout_request_id),
                checkout_fingerprint=fingerprint,
                created_at = datetime.now(timezone.utc)
            )
            
            self.db.add(new_order)
            await self.db.flush() # الحصول على new_order.id دون عمل Commit
            
            # ربط العناصر بالطلب بعد الحصول على الـ ID
            for order_item in order_items_to_create:
                order_item.order_id = new_order.id
            
            self.db.add_all(order_items_to_create)
            provider_key = "checkout_" + uuid.uuid4().hex
            payment_request = PaymentRequest(
                order_id=str(new_order.id), amount=total_amount, currency=new_order.currency,
                preferred_provider=selected_provider, shipping_address=payload.shipping_address,
                region=payload.shipping_address.country, idempotency_key=provider_key,
                metadata={"user_id": str(payload.user_id), "correlation_id": provider_key,
                          "source": "ai_chat_checkout"},
            )
            new_order.checkout_data = {
                "cart_snapshot": original_cart,
                "payment_request": payment_request.model_dump(mode="json"),
                "ui_items": [{"id": item["product_id"], "name": item["name"],
                              "quantity": item["quantity"], "price": float(item["price"])}
                             for item in verified_items],
            }
            self.db.add(new_order)
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

        except IntegrityError:
            # The uniqueness constraint is the authority. A losing concurrent
            # creation rolls back its order/items before any provider call.
            await self.db.rollback()
            existing = await self._find_checkout(payload.user_id, str(payload.checkout_request_id))
            if existing is not None:
                return await self._resume_checkout(existing, fingerprint)
            logger.exception("Checkout integrity failure unrelated to request replay")
            return {"status": "pending", "message": "Checkout could not be reconciled."}

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

        return await self._resume_checkout(new_order, fingerprint)

    async def _find_checkout(self, user_id: int, request_id: str) -> Optional[Order]:
        result = await self.db.execute(select(Order).where(Order.user_id == user_id,
                                                         Order.checkout_request_id == request_id))
        return result.scalars().one_or_none()

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    async def _resume_checkout(self, order: Order, fingerprint: str) -> Dict[str, Any]:
        order = await self.db.get(Order, order.id, with_for_update=True, populate_existing=True)
        if order.checkout_fingerprint != fingerprint:
            await self.db.commit()
            return {"status": "conflict", "order_id": order.id,
                    "message": "This checkout key belongs to different delivery or payment details."}
        if order.is_paid:
            await self.db.commit()
            return {"status": "paid", "order_id": order.id}
        now = datetime.now(timezone.utc)
        if (order.status not in {OrderStatus.PENDING, OrderStatus.FAILED}
                or self._utc(order.created_at) + timedelta(hours=1) <= now):
            await self.db.commit()
            return {"status": "reconciliation_required", "order_id": order.id,
                    "message": "Review the existing order before starting another payment."}
        snapshot = order.checkout_data or {}
        if snapshot.get("handoff"):
            await self.db.commit()
            return {"status": "ready", "order_id": order.id, "payment": snapshot["handoff"]}
        if order.payment_setup_lease_until and self._utc(order.payment_setup_lease_until) > now:
            await self.db.commit()
            return {"status": "pending", "order_id": order.id}
        try:
            payment_request = PaymentRequest.model_validate(snapshot["payment_request"])
        except (KeyError, ValueError):
            await self.db.commit()
            return {"status": "reconciliation_required", "order_id": order.id}
        order.payment_setup_generation += 1
        generation = order.payment_setup_generation
        order.payment_setup_lease_until = now + timedelta(seconds=30)
        self.db.add(order)
        await self.db.commit()  # Never hold a database lock during provider I/O.
        try:
            response = await asyncio.wait_for(self.orchestrator.process_payment(
                request=payment_request, corr_id=payment_request.metadata["correlation_id"]), timeout=8.0)
            gateway = response.primary_gateway
            if (response.status != PaymentStatus.SUCCESS or gateway is None
                    or not (gateway.client_secret or gateway.action_url)
                    or not isinstance(gateway.transaction_id, str) or not gateway.transaction_id
                    or len(gateway.transaction_id) > 255):
                return await self._setup_uncertain(order.id, generation)
        except asyncio.CancelledError:
            # Keep the durable lease. Another process can reconcile it after expiry.
            raise
        except Exception:
            logger.warning("Payment setup outcome uncertain", extra={"order_id": order.id})
            return await self._setup_uncertain(order.id, generation)

        returned_provider = getattr(gateway.provider, "value", gateway.provider)
        expected_provider = getattr(payment_request.preferred_provider, "value", payment_request.preferred_provider)
        if returned_provider not in {"stripe", "paypal"} or returned_provider != expected_provider:
            logger.warning("Payment setup returned a different provider", extra={"order_id": order.id})
            return await self._setup_uncertain(order.id, generation)

        order = await self.db.get(Order, order.id, with_for_update=True, populate_existing=True)
        if order.payment_setup_generation != generation:
            await self.db.commit()
            return {"status": "pending", "order_id": order.id}
        if order.is_paid:
            await self.db.commit()
            return {"status": "paid", "order_id": order.id}
        if (order.status not in {OrderStatus.PENDING, OrderStatus.FAILED}
                or (order.payment_transaction_id and order.payment_transaction_id != gateway.transaction_id)):
            await self.db.commit()
            return {"status": "reconciliation_required", "order_id": order.id}
        provider = getattr(gateway.provider, "value", gateway.provider)
        handoff = {"checkout_request_id": order.checkout_request_id, "client_secret": gateway.client_secret, "action_url": gateway.action_url,
                   "gateway_provider": provider,
                   "order_data": {"order_id": order.id, "total": float(order.total_price),
                                  "currency": order.currency, "items": snapshot["ui_items"]}}
        order.payment_transaction_id = gateway.transaction_id
        if provider == "stripe":
            order.stripe_payment_id = gateway.transaction_id
        order.checkout_data = {**snapshot, "handoff": handoff}
        order.payment_setup_lease_until = None
        self.db.add(order)
        order_id = order.id
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            return {"status": "pending", "order_id": order_id}
        await self._send_to_ui(order.user_id, {"type": "payment_intent", "content": handoff})
        return {"status": "ready", "order_id": order.id, "payment": handoff}

    async def _setup_uncertain(self, order_id: int, generation: int) -> Dict[str, Any]:
        order = await self.db.get(Order, order_id, with_for_update=True, populate_existing=True)
        if order.payment_setup_generation == generation:
            order.payment_setup_lease_until = None
            self.db.add(order)
        await self.db.commit()
        if order.is_paid:
            return {"status": "paid", "order_id": order_id}
        await self._send_error(order.user_id, "Payment setup could not be confirmed. Retry this same checkout or review your existing order.")
        return {"status": "pending", "order_id": order_id}

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

            if order.user_id != payload.user_id:
                logger.warning("Payment success owner mismatch", extra={"order_id": payload.order_id})
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

            await self._send_to_ui(payload.user_id, {
                "content": f"Payment Secured! Order #{order.id} is confirmed and being prepared for delivery.",
                "type": "success_text"
            })

            self._emit_analytics_event(
                "airdeliver.ai.analytics.conversion",
                {"user_id": payload.user_id, "order_id": order.id, "revenue": str(order.total_price)}
            )

        except Exception as e:
            await self.db.rollback()
            logger.critical("Critical failure in payment success handler", extra={"order_id": payload.order_id, "error": str(e)})
            await self._send_to_ui(payload.user_id, {
                "content": "Payment status could not be confirmed here. Check your existing order before paying again.",
                "type": "error",
            })

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

                    elif order.status in {OrderStatus.PROCESSING, OrderStatus.ASSIGNED, OrderStatus.IN_TRANSIT}:
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
