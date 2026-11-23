# apps/api/app/services/ai_cart_service.py

import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any, Final, Sequence

from pydantic import BaseModel, Field, ValidationError, field_validator, PrivateAttr
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.services.ai_commerce_engine import AICommerceEngine

from app.schemas.cart_recommendation import CartRecommendationEvent, CART_RECOMMENDATION_ROUTING_KEY
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason
from app.services.free_llm_service import FreeLLMService
logger = logging.getLogger("airdeliver.cart")


class CartPersistenceError(RuntimeError):
    """Cart outcome cannot be confirmed. Never present this as an empty cart."""


# --- DOMAIN STATE MODELS ---

class CartItemModel(BaseModel):
    product_id: int = Field(ge=1, le=9223372036854775807, strict=True)
    name: str
    quantity: int = Field(ge=1, le=99, strict=True)
    price: Decimal = Field(ge=0, allow_inf_nan=False)
    image_url: str = ""
    category: str = ""

class CartStateModel(BaseModel):
    _snapshot: Any = PrivateAttr(default=None)
    items: List[CartItemModel] = Field(default_factory=list)
    total: Decimal = Field(default=Decimal("0.00"), ge=0, allow_inf_nan=False)
    updated_at: str = ""

class CartOperationPayload(BaseModel):
    user_id: int = Field(ge=1, le=9223372036854775807)
    product_id: Optional[int] = Field(default=None, ge=1, le=9223372036854775807)
    quantity: int = Field(default=1, ge=1, le=99)

    @field_validator("user_id", "product_id", "quantity", mode="before")
    @classmethod
    def reject_boolean_identifiers_and_quantity(cls, value):
        if isinstance(value, bool):
            raise ValueError("Boolean is not an identifier or quantity")
        return value
    action: str = "default"
    notify_user: bool = True


class AICartService:
    """
    🛒 DIAMOND CART SERVICE (V4.1 - ENTERPRISE EDITION).

    Architectural Guarantees:
    1. Financial Precision: Immutable Decimal arithmetic for all pricing.
    2. Transactional Safety: Strict database session boundaries and rollbacks.
    3. Type Safety: Pydantic-enforced state hydration/dehydration.
    4. Deterministic Lifecycle: Guaranteed resource release and deterministic cache TTLs.
    """

    CART_KEY_PREFIX = "ai_cart:"
    CART_TTL_SECONDS = 86400
    UI_CHANNEL_PREFIX = "airdeliver:response:"

    def __init__(
        self,
        db: AsyncSession,
        cache: IAsyncCacheClient,
        rabbitmq: RabbitMQService,
        commerce_engine: Optional[AICommerceEngine] = None,
        llm_service: Optional[FreeLLMService] = None
    ):
        self.db = db
        self.cache = cache
        self.rabbitmq = rabbitmq
        self.commerce_engine = commerce_engine
        self.llm_service = llm_service

    # --- 🔌 UI RESPONSE ROUTER ---

    # --- 🔄 COMMAND: STATE RECONCILIATION ---
    async def handle_sync_cart(self, raw_payload: dict) -> None:
        """
        Deterministically synchronizes the authoritative Redis cart state with the ephemeral UI state.
        Executed strictly upon WebSocket connection establishment to prevent split-brain UI state.
        """
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError as exc:
            logger.warning(
                "cart_sync_payload_invalid",
                extra={"error": exc.errors(), "user_id": raw_payload.get("user_id")}
            )
            return

        try:
            # 1. Retrieve authoritative state
            cart = await self._get_cart_from_redis(payload.user_id)

            # 2. Push state to edge regardless of item count to guarantee deterministic UI hydration
            # (If the cart is empty, the UI must know it is empty, overriding any ghost state).
            await self._send_to_ui(payload.user_id, {
                "content": cart.model_dump(mode='json'),
                "type": "cart_preview",
                "reason": "CONNECTION_STATE_RECONCILIATION"
            })

            logger.info(
                "cart_state_synchronized",
                extra={"user_id": payload.user_id, "item_count": len(cart.items)}
            )
        except CartPersistenceError:
            raise
        except Exception as exc:
            logger.error(
                "cart_sync_critical_failure",
                extra={"user_id": payload.user_id, "error": str(exc)},
                exc_info=True
            )

    async def _send_to_ui(self, user_id: int, payload: Dict[str, Any]) -> None:
        """
        Pushes deterministic, strictly serialized payloads to the WebSocket edge.
        """
        try:
            channel = f"{self.UI_CHANNEL_PREFIX}{user_id}"

            payload["meta"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "ai_cart_v4.1"
            }

            def _strict_serializer(obj: Any) -> Any:
                if isinstance(obj, datetime):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return str(obj)  # Financial precision guarantee over JSON
                raise TypeError(f"Type {type(obj)} not serializable")

            message = json.dumps(payload, default=_strict_serializer)
            await self.cache.publish(channel, message)
        except Exception as e:
            logger.error(
                "UI delivery pipeline failure",
                extra={"user_id": user_id, "error": str(e)}
            )

    # --- 🛠️ STATE MANAGEMENT ---
    def _get_cart_key(self, user_id: int) -> str:
        return f"{self.CART_KEY_PREFIX}{user_id}"

    async def _get_cart_from_redis(self, user_id: int) -> CartStateModel:
        """
        Rehydrates strict domain models from Redis RAM.
        """
        try:
            raw_cart = await self.cache.get_json_required(self._get_cart_key(user_id))
            cart = CartStateModel() if raw_cart is None else CartStateModel.model_validate(raw_cart)
            cart._snapshot = raw_cart
            return cart
        except Exception as exc:
            logger.error("cart required read failed", extra={"error_type": type(exc).__name__})
            raise CartPersistenceError("Cart could not be read; current state was preserved") from exc

    async def _update_cart_in_redis(self, user_id: int, cart: CartStateModel) -> None:
        """
        Calculates financial totals deterministically and persists to distributed cache.
        """
        try:
            cart.total = sum((item.price * Decimal(item.quantity) for item in cart.items), Decimal("0.00"))
            cart.updated_at = datetime.now(timezone.utc).isoformat()

            # Ensure safe JSON serialization of Decimals via Pydantic
            cart_dict = cart.model_dump(mode='json')

            confirmed = await self.cache.compare_json_required(self._get_cart_key(user_id), cart._snapshot, cart_dict, ttl=self.CART_TTL_SECONDS)
            if not confirmed:
                raise CartPersistenceError("Cart changed concurrently; refresh before retrying")
            cart._snapshot = cart_dict

            await self._send_to_ui(user_id, {
                "content": cart_dict,
                "type": "cart_preview",
                "reason": "State Sync"
            })
        except Exception as e:
            logger.error("cart required write failed", extra={"error_type": type(e).__name__})
            raise CartPersistenceError("Cart update could not be confirmed; refresh before retrying") from e

    # --- ➕ COMMAND: ADD TO CART ---
    async def handle_add_to_cart(self, raw_payload: dict) -> None:
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError as e:
            logger.warning("Malformed add-to-cart payload", extra={"error": str(e)})
            return

        if not payload.product_id:
            return

        product = await self.db.get(Product, payload.product_id, populate_existing=True)
        if not product or not product.is_active or product.inventory <= 0:
            if payload.notify_user:
                await self._send_to_ui(payload.user_id, {"content": "Product unavailable or out of stock.", "type": "error"})
            return

        cart = await self._get_cart_from_redis(payload.user_id)

        existing_item = next((item for item in cart.items if item.product_id == payload.product_id), None)

        total_quantity = payload.quantity + (existing_item.quantity if existing_item else 0)
        if total_quantity > 99 or total_quantity > product.inventory:
            if payload.notify_user:
                await self._send_to_ui(payload.user_id, {
                    "content": "The requested quantity is unavailable. Your cart has not changed.",
                    "type": "error",
                })
            return

        if existing_item:
            existing_item.quantity = total_quantity
            # A cached line is not authority for mutable catalog facts.
            existing_item.price = Decimal(str(product.price))
            existing_item.name = product.name
            existing_item.category = getattr(product, 'category', '')
            existing_item.image_url = getattr(product, 'image_url', '')
        else:
            cart.items.append(CartItemModel(
                product_id=product.id,
                name=product.name,
                quantity=payload.quantity,
                price=Decimal(str(product.price)),
                image_url=getattr(product, 'image_url', ''),
                category=getattr(product, 'category', '')
            ))

        await self._update_cart_in_redis(payload.user_id, cart)

        if payload.notify_user:
            await self._send_to_ui(payload.user_id, {
                "content": f"{product.name} added to your cart. Stock is checked again at checkout.",
                "type": "success_text"
            })

            # Vector Bundle Engine Injection
            if self.commerce_engine:
                await self._trigger_intelligent_bundling(payload.user_id, product)
            else:
                await self._request_optional_recommendations(payload.user_id, int(product.id), "added")

            await self._send_to_ui(payload.user_id, {
                "type": "confirmation_prompt",
                "options": ["Confirm Order"]
            })

    async def _request_optional_recommendations(self, user_id: int, product_id: int, operation: str) -> None:
        """Read-only follow-up. Broker failure must never undo a saved cart."""
        try:
            event = CartRecommendationEvent(user_id=user_id, product_id=product_id, operation=operation)
            async with asyncio.timeout(1.0):
                outcome = await self.rabbitmq.publish(event.model_dump(), CART_RECOMMENDATION_ROUTING_KEY, max_retries=1)
            if not outcome.is_success:
                logger.warning("cart optional recommendation event unconfirmed")
        except Exception as exc:
            logger.warning("cart optional recommendation unavailable", extra={"error_type": type(exc).__name__})

    async def _trigger_intelligent_bundling(self, user_id: int, product: Product) -> None:
        BUNDLE_FETCH_TIMEOUT_SECONDS: Final[float] = 120.0
        COPY_GENERATION_TIMEOUT_SECONDS: Final[float] = 2.0
        MAX_BUNDLE_NAME_CONTEXT_ITEMS: Final[int] = 4
        MAX_DYNAMIC_COPY_LENGTH: Final[int] = 160
        FALLBACK_REASON: Final[str] = "Synergy Analysis"

        if not self.commerce_engine:
            logger.debug(
                "intelligent_bundling_skipped",
                extra={
                    "user_id": user_id,
                    "reason": "commerce_engine_unavailable",
                },
            )
            return

        def _normalize_text(value: Any) -> str:
            if value is None:
                return ""
            return " ".join(str(value).strip().split())

        def _truncate(value: str, max_length: int) -> str:
            if len(value) <= max_length:
                return value
            return value[: max_length - 1].rstrip() + "…"

        def _safe_product_name(item: Any) -> str:
            name = _normalize_text(getattr(item, "name", ""))
            return name or "complementary item"

        def _fallback_copy() -> str:
            product_name = _safe_product_name(product)
            return f"A technically precise extension of your {product_name} selection."

        async def _generate_bundle_copy(bundle_items: Sequence[Product]) -> str:
           bundle_names = ", ".join(
               _safe_product_name(item)
               for item in bundle_items[:MAX_BUNDLE_NAME_CONTEXT_ITEMS]
           )

           primary_product_name = _safe_product_name(product)
           
           system_role = "You are an elite AI shopping concierge."
           
           prompt = (
                "You are an elite AI shopping concierge.\n"
                f"The user just added '{primary_product_name}' to their cart.\n"
                f"I am instantly recommending these complementary items: {bundle_names}.\n\n"
                "Write a single sophisticated sentence explaining why this exact combination is technically, "
                "aesthetically, or functionally strong.\n"
                "Rules:\n"
                "- Maximum 20 words.\n"
                "- No generic phrases such as 'perfect match', 'pairs well with', or 'enhance your experience'.\n"
                "- Be precise, confident, and natural.\n"
                "- Do not sound promotional.\n"
                "- Output only the sentence."
           )

           raw_response = await self.llm_service.generate_response(
               prompt=prompt,
               system_role=system_role,
               temperature=0.4
           )
           candidate = _normalize_text(raw_response).strip(' "\'')

           if not candidate:
               return _fallback_copy()

           return _truncate(candidate, MAX_DYNAMIC_COPY_LENGTH)

        try:
            logger.info(
                "intelligent_bundling_started",
                extra={
                    "user_id": user_id,
                    "product_name": _safe_product_name(product),
                },
            )

            try:
                async with asyncio.timeout(BUNDLE_FETCH_TIMEOUT_SECONDS):
                    bundle_items = await self.commerce_engine.generate_perfect_bundle(self.db, product)
            except TimeoutError:
                logger.warning(
                    "intelligent_bundling_bundle_fetch_timed_out",
                    extra={
                        "user_id": user_id,
                        "product_name": _safe_product_name(product),
                        "timeout_seconds": BUNDLE_FETCH_TIMEOUT_SECONDS,
                    },
                )
                return

            if not bundle_items:
                logger.info(
                    "intelligent_bundling_no_candidates",
                    extra={
                        "user_id": user_id,
                        "product_name": _safe_product_name(product),
                    },
                )
                return

            try:
                async with asyncio.timeout(COPY_GENERATION_TIMEOUT_SECONDS):
                    dynamic_ai_copy = await _generate_bundle_copy(bundle_items)
            except TimeoutError:
                logger.warning(
                    "intelligent_bundling_copy_generation_timed_out",
                    extra={
                        "user_id": user_id,
                        "product_name": _safe_product_name(product),
                        "timeout_seconds": COPY_GENERATION_TIMEOUT_SECONDS,
                    },
                )
                dynamic_ai_copy = _fallback_copy()
            except Exception as exc:
                logger.warning(
                    "intelligent_bundling_copy_generation_failed",
                    extra={
                        "user_id": user_id,
                        "product_name": _safe_product_name(product),
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                dynamic_ai_copy = _fallback_copy()

            payload = {
                "content": dynamic_ai_copy,
                "type": "product_carousel",
                 "products": [item.model_dump(mode="json") for item in bundle_items],
                 "secondary_suggestions": True,
                 "reason": FALLBACK_REASON,
            }

            await self._send_to_ui(user_id, payload)

            logger.info(
                "intelligent_bundling_completed",
                extra={
                    "user_id": user_id,
                    "product_name": _safe_product_name(product),
                    "bundle_size": len(bundle_items),
                },
            )

        except asyncio.CancelledError:
            logger.info(
                "intelligent_bundling_cancelled",
                extra={
                    "user_id": user_id,
                    "product_name": _safe_product_name(product),
                },
            )
            raise

        except Exception as exc:
            logger.exception(
                "intelligent_bundling_failed",
                extra={
                    "user_id": user_id,
                    "product_name": _safe_product_name(product),
                    "error": str(exc),
                },
            )

    # --- 💾 COMMAND: SAVE CART ---
    async def handle_save_cart(self, raw_payload: dict) -> dict:
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError:
            return {"status": "rejected"}

        cart = await self._get_cart_from_redis(payload.user_id)
        if not cart.items:
            await self._send_to_ui(payload.user_id, {"content": "Nothing to save.", "type": "error"})
            return {"status": "empty"}

        try:
            saved_order = Order(
                user_id=payload.user_id,
                status=OrderStatus.CANCELLED,
                cancellation_reason=CancellationReason.CHANGED_MIND,
                total_price=cart.total,
                delivery_address="Saved List",
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(saved_order)
            await self.db.flush()

            for item in cart.items:
                self.db.add(OrderItem(
                    order_id=saved_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price_per_unit=item.price
                ))

            await self.db.commit()

            try:
                confirmed = await self.cache.compare_json_required(self._get_cart_key(payload.user_id), cart._snapshot, None, delete=True)
                if not confirmed:
                    raise CartPersistenceError("Active cart changed while saving")
            except Exception as exc:
                logger.warning("saved cart committed but cache cleanup unconfirmed", extra={"error_type": type(exc).__name__})
                await self._send_to_ui(payload.user_id, {
                    "content": "Your saved list was recorded, but clearing the active cart could not be confirmed. Refresh your cart before saving again.",
                    "type": "error",
                })
                return {"status": "cleanup_unconfirmed", "saved_order_id": saved_order.id}

            await self._send_to_ui(payload.user_id, {
                "content": "Your list was saved to your profile and the active cart was cleared.",
                "type": "success_text"
            })

            await self._send_to_ui(payload.user_id, {
                "content": CartStateModel().model_dump(mode='json'),
                "type": "cart_preview"
            })
            return {"status": "saved", "saved_order_id": saved_order.id}

        except Exception as e:
            await self.db.rollback()
            logger.error("Database transaction failed during cart save", extra={"user_id": payload.user_id, "error": str(e)})
            await self._send_to_ui(payload.user_id, {"content": "Saving your list could not be confirmed. Check your saved lists before saving again.", "type": "error"})
            return {"status": "save_unconfirmed"}

    # --- ➖ COMMAND: REMOVE FROM CART ---
    # --- ➖ COMMAND: REMOVE FROM CART ---
    async def handle_remove_from_cart(self, raw_payload: dict) -> None:
    
        ALT_SEARCH_TIMEOUT_SECONDS: Final[float] = float(os.getenv("ALT_SEARCH_TIMEOUT", "15.0"))
        COPY_GEN_TIMEOUT_SECONDS: Final[float] = float(os.getenv("COPY_GEN_TIMEOUT", "25.0"))
        UI_CONFIRMATION_DELAY_SECONDS: Final[float] = 0.1
        MAX_RECOVERY_COPY_LENGTH: Final[int] = 160
        ALTERNATIVES_LIMIT: Final[int] = 3
        DEFAULT_ALTERNATIVE_REASON: Final[str] = "Smart Alternative"

        def _normalize_text(value: Any) -> str:
            if value is None:
                return ""
            return " ".join(str(value).strip().split())

        def _truncate(value: str, max_length: int) -> str:
            if len(value) <= max_length:
                return value
            return value[: max_length - 1].rstrip() + "…"

        def _safe_decimal(value: Any, default: str = "0") -> Decimal:
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal(default)

        def _safe_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        def _safe_product_name(item: Any, fallback: str = "item") -> str:
            name = _normalize_text(getattr(item, "name", ""))
            return name or fallback

        def _build_removal_message(item_name: str) -> str:
            return f"Removed {item_name}. Cart updated."

        def _build_recovery_fallback(item_name: str) -> str:
            return f"I noticed you removed {item_name}. Here is a sharper alternative."

        def _derive_alternative_reason(removed_item: Any, alternative: Any) -> str:
            alternative_price = _safe_decimal(getattr(alternative, "price", 0))
            alternative_rating = _safe_float(getattr(alternative, "rating", 0.0))
            removed_price = _safe_decimal(getattr(removed_item, "price", 0))

            if alternative_rating > 4.5:
                return f"Users rated this {alternative_rating:.1f}/5 ⭐"
            if alternative_price < removed_price:
                diff = removed_price - alternative_price
                return f"Save ${diff:.2f} with this choice 💰"
            if alternative_price > removed_price:
                return "Treat yourself to a premium alternative ✨"
            return "A trending alternative in this category 🔥"

        async def _find_alternatives(payload: CartOperationPayload) -> Sequence[Product]:
            if not self.commerce_engine or payload.action == "clear_all":
                return []

            try:
                async with asyncio.timeout(ALT_SEARCH_TIMEOUT_SECONDS):
                    alternatives = await self.commerce_engine.find_genius_alternatives(
                        self.db,
                        payload.product_id,
                        limit=ALTERNATIVES_LIMIT,
                    )
                    return alternatives or []
            except TimeoutError:
                logger.warning(
                    "genius_alternatives_search_timeout",
                    extra={
                        "user_id": payload.user_id,
                        "product_id": payload.product_id,
                        "timeout_seconds": ALT_SEARCH_TIMEOUT_SECONDS,
                    },
                )
                return []
            except Exception as exc:
                logger.warning(
                    "genius_alternatives_search_failed",
                    extra={
                        "user_id": payload.user_id,
                        "product_id": payload.product_id,
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                return []

        async def _generate_recovery_copy(
            payload: CartOperationPayload,
            removed_item: Any,
            alternative: Any,
        ) -> str:
            removed_name = _safe_product_name(removed_item)
            alternative_name = _safe_product_name(alternative)
            removed_price = _safe_decimal(getattr(removed_item, "price", 0))
            alternative_price = _safe_decimal(getattr(alternative, "price", 0))
            fallback_message = _build_recovery_fallback(removed_name)

            if not self.llm_service:
                return fallback_message
            
            system_role = "You are an elite AI shopping concierge."
            
            prompt = (
                "You are an elite AI shopping concierge.\n"
                f"The user removed '{removed_name}' (Price: ${removed_price}) from their cart.\n"
                f"I am instantly recommending '{alternative_name}' (Price: ${alternative_price}) as a replacement.\n\n"
                "Write a single empathetic and smooth sentence that acknowledges the removal and naturally pivots "
                "to the replacement.\n"
                "Rules:\n"
                "- Maximum 15 words.\n"
                "- Be conversational and confident.\n"
                "- Do not use generic phrases like 'Check this out instead'.\n"
                "- Output only the sentence."
            )

            try:
                async with asyncio.timeout(COPY_GEN_TIMEOUT_SECONDS):
                    raw_response = await self.llm_service.generate_response(
                        prompt=prompt,
                        system_role="You are an elite AI shopping concierge.",
                        temperature=0.4,
                    )
            except TimeoutError:
                logger.warning(
                    "recovery_copy_generation_timeout",
                    extra={
                        "user_id": payload.user_id,
                        "product_id": payload.product_id,
                        "timeout_seconds": COPY_GEN_TIMEOUT_SECONDS,
                    },
                )
                return fallback_message
            except Exception as exc:
                logger.warning(
                    "recovery_copy_generation_failed",
                    extra={
                        "user_id": payload.user_id,
                        "product_id": payload.product_id,
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                return fallback_message

            candidate = _normalize_text(raw_response).strip(' "\'')

            if not candidate:
                return fallback_message

            return _truncate(candidate, MAX_RECOVERY_COPY_LENGTH)

        async def _dispatch_recovery_ui(
            payload: CartOperationPayload,
            response_message: str,
            alternatives: Sequence[Product],
            reason: Optional[str],
        ) -> None:
            await self._send_to_ui(
                payload.user_id,
                {
                    "content": response_message,
                    "type": "product_carousel" if alternatives else "success_text",
                    "products": [item.model_dump(mode="json") for item in alternatives] if alternatives else [],
                    "reason": reason if alternatives else None,
                },
            )

        try:
            try:
                payload = CartOperationPayload(**raw_payload)
            except ValidationError as exc:
                logger.warning(
                    "remove_from_cart_payload_invalid",
                    extra={
                        "error_count": exc.error_count(),
                    },
                )
                return

            if not payload.product_id:
                logger.debug(
                    "remove_from_cart_skipped",
                    extra={
                        "user_id": payload.user_id,
                        "reason": "missing_product_id",
                    },
                )
                return

            logger.info(
                "remove_from_cart_started",
                extra={
                    "user_id": payload.user_id,
                    "product_id": payload.product_id,
                    "notify_user": payload.notify_user,
                    "action": _normalize_text(payload.action),
                },
            )

            cart = await self._get_cart_from_redis(payload.user_id)

            item_to_remove = next(
                (item for item in cart.items if item.product_id == payload.product_id),
                None,
            )

            if not item_to_remove:
                await self._update_cart_in_redis(payload.user_id, cart)
                logger.info(
                    "remove_from_cart_item_missing",
                    extra={
                        "user_id": payload.user_id,
                        "product_id": payload.product_id,
                    },
                )
                return

            cart.items = [
                item for item in cart.items
                if item.product_id != item_to_remove.product_id
            ]
            await self._update_cart_in_redis(payload.user_id, cart)

            if not payload.notify_user:
                logger.info(
                    "remove_from_cart_completed_without_notification",
                    extra={
                        "user_id": payload.user_id,
                        "product_id": payload.product_id,
                        "remaining_items": len(cart.items),
                    },
                )
                return

            if not self.commerce_engine and payload.action != "clear_all":
                await self._request_optional_recommendations(payload.user_id, int(payload.product_id), "removed")

            alternatives = await _find_alternatives(payload)

            if alternatives:
                best_alternative = alternatives[0]
                ai_reason = _derive_alternative_reason(item_to_remove, best_alternative)
                response_message = await _generate_recovery_copy(
                    payload,
                    item_to_remove,
                    best_alternative,
                )
            else:
                ai_reason = None
                response_message = _build_removal_message(_safe_product_name(item_to_remove))

            await _dispatch_recovery_ui(
                payload,
                response_message,
                alternatives,
                ai_reason or DEFAULT_ALTERNATIVE_REASON if alternatives else None,
            )

            if cart.items:
                await asyncio.sleep(UI_CONFIRMATION_DELAY_SECONDS)
                await self._send_to_ui(
                    payload.user_id,
                    {
                        "content": None,
                        "type": "confirmation_prompt",
                        "options": ["Confirm Order", "Keep Shopping"],
                    },
                )

            self._emit_analytics_event(
                payload.user_id,
                item_to_remove.product_id,
                "smart_recovery_triggered" if alternatives else "removal",
            )

            logger.info(
                "remove_from_cart_completed",
                extra={
                    "user_id": payload.user_id,
                    "product_id": item_to_remove.product_id,
                    "alternatives_found": len(alternatives),
                    "remaining_items": len(cart.items),
                },
            )

        except asyncio.CancelledError:
            logger.info(
                "remove_from_cart_cancelled",
                extra={},
            )
            raise
        except CartPersistenceError:
            raise
        except Exception as exc:
            logger.exception(
                "remove_from_cart_failed",
                extra={
                    "error": str(exc),
                },
            )
    def _emit_analytics_event(self, user_id: int, product_id: int, action: str) -> None:
        """Fire-and-forget background analytics emission."""
        async def _publish() -> None:
            try:
                await self.rabbitmq.publish(
                    {
                        "user_id": user_id,
                        "removed_product_id": product_id,
                        "action": action,
                        "timestamp": datetime.now(timezone.utc).timestamp()
                    },
                    "airdeliver.ai.intent.removal_recovery"
                )
            except Exception as e:
                logger.error("Analytics emission failed", extra={"error": str(e)})

        asyncio.create_task(_publish())

    # --- 🧹 COMMAND: CLEAR CART ---
    async def handle_clear_cart(self, raw_payload: dict) -> None:
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError:
            return

        try:
            await self.cache.delete_required(self._get_cart_key(payload.user_id))
        except Exception as exc:
            raise CartPersistenceError("Cart clear could not be confirmed; refresh before retrying") from exc

        try:
            statement = select(Order).where(
                Order.user_id == payload.user_id,
                Order.status == OrderStatus.PENDING
            )
            results = (await self.db.execute(statement)).scalars().all()

            if results:
                for order in results:
                    order.status = OrderStatus.CANCELLED
                    self.db.add(order)
                await self.db.commit()
                logger.info("Pending orders cancelled", extra={"user_id": payload.user_id, "count": len(results)})
        except Exception as e:
            await self.db.rollback()
            logger.error("Order database cleanup failure", extra={"user_id": payload.user_id, "error": str(e)})

        await self._send_to_ui(payload.user_id, {
            "content": CartStateModel().model_dump(mode='json'),
            "type": "cart_preview",
            "reason": "Clear Command"
        })
