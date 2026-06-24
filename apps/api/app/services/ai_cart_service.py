# apps/api/app/services/ai_cart_service.py

import json
import logging
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.services.ai_commerce_engine import AICommerceEngine

from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus, CancellationReason

logger = logging.getLogger("airdeliver.cart")


# --- DOMAIN STATE MODELS ---

class CartItemModel(BaseModel):
    product_id: int
    name: str
    quantity: int = Field(gt=0)
    price: Decimal
    image_url: str = ""
    category: str = ""

class CartStateModel(BaseModel):
    items: List[CartItemModel] = Field(default_factory=list)
    total: Decimal = Field(default=Decimal("0.00"))
    updated_at: str = ""

class CartOperationPayload(BaseModel):
    user_id: int
    product_id: Optional[int] = None
    quantity: int = 1
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
        commerce_engine: Optional[AICommerceEngine] = None
    ):
        self.db = db
        self.cache = cache
        self.rabbitmq = rabbitmq
        self.commerce_engine = commerce_engine

    # --- 🔌 UI RESPONSE ROUTER ---
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
            raw_cart = await self.cache.get_json(self._get_cart_key(user_id))
            if raw_cart:
                return CartStateModel(**raw_cart)
        except ValidationError as ve:
            logger.error("Cart state corruption detected, resetting state", extra={"user_id": user_id, "error": str(ve)})
        except Exception as e:
            logger.error("Redis fetch failure", extra={"user_id": user_id, "error": str(e)})

        return CartStateModel()

    async def _update_cart_in_redis(self, user_id: int, cart: CartStateModel) -> None:
        """
        Calculates financial totals deterministically and persists to distributed cache.
        """
        try:
            cart.total = sum((item.price * Decimal(item.quantity) for item in cart.items), Decimal("0.00"))
            cart.updated_at = datetime.now(timezone.utc).isoformat()

            # Ensure safe JSON serialization of Decimals via Pydantic
            cart_dict = cart.model_dump(mode='json')

            await self.cache.set_json(self._get_cart_key(user_id), cart_dict, ttl=self.CART_TTL_SECONDS)

            await self._send_to_ui(user_id, {
                "content": cart_dict,
                "type": "cart_preview",
                "reason": "State Sync"
            })
        except Exception as e:
            logger.error("Redis persistence failure", extra={"user_id": user_id, "error": str(e)})

    # --- ➕ COMMAND: ADD TO CART ---
    async def handle_add_to_cart(self, raw_payload: dict) -> None:
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError as e:
            logger.warning("Malformed add-to-cart payload", extra={"error": str(e)})
            return

        if not payload.product_id:
            return

        product = await self.db.get(Product, payload.product_id)
        if not product:
            if payload.notify_user:
                await self._send_to_ui(payload.user_id, {"content": "Product unavailable or out of stock.", "type": "error"})
            return

        cart = await self._get_cart_from_redis(payload.user_id)

        existing_item = next((item for item in cart.items if item.product_id == payload.product_id), None)

        if existing_item:
            existing_item.quantity += payload.quantity
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
                "content": f"{product.name} secured in manifest.",
                "type": "success_text"
            })

            # Vector Bundle Engine Injection
            if self.commerce_engine:
                await self._trigger_intelligent_bundling(payload.user_id, product)

            await self._send_to_ui(payload.user_id, {
                "type": "confirmation_prompt",
                "options": ["Confirm Order"]
            })

    async def _trigger_intelligent_bundling(self, user_id: int, product: Product) -> None:
        if not self.commerce_engine:
            return

        try:
            bundle_items = await self.commerce_engine.generate_perfect_bundle(self.db, product)
            if bundle_items:
                await self._send_to_ui(user_id, {
                    "content": f"Enhance your {product.name} experience with these:",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in bundle_items],
                    "secondary_suggestions": True,
                    "reason": "Rigorously curated complementary selection."
                })
        except Exception as e:
            logger.error("Vector bundling engine failure", extra={"error": str(e)})

    # --- 💾 COMMAND: SAVE CART ---
    async def handle_save_cart(self, raw_payload: dict) -> None:
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError:
            return

        cart = await self._get_cart_from_redis(payload.user_id)
        if not cart.items:
            await self._send_to_ui(payload.user_id, {"content": "Nothing to save.", "type": "error"})
            return

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

            await self.cache.delete(self._get_cart_key(payload.user_id))

            await self._send_to_ui(payload.user_id, {
                "content": "Done! You can restore it from your profile.",
                "type": "success_text"
            })

            await self._send_to_ui(payload.user_id, {
                "content": CartStateModel().model_dump(mode='json'),
                "type": "cart_preview"
            })

        except Exception as e:
            await self.db.rollback()
            logger.error("Database transaction failed during cart save", extra={"user_id": payload.user_id, "error": str(e)})
            await self._send_to_ui(payload.user_id, {"content": "Failed to save cart.", "type": "error"})

    # --- ➖ COMMAND: REMOVE FROM CART ---
    async def handle_remove_from_cart(self, raw_payload: dict) -> None:
        try:
            payload = CartOperationPayload(**raw_payload)
        except ValidationError:
            return

        if not payload.product_id:
            return

        cart = await self._get_cart_from_redis(payload.user_id)

        item_to_remove = next((item for item in cart.items if item.product_id == payload.product_id), None)

        if item_to_remove:
            cart.items = [item for item in cart.items if item.product_id != item_to_remove.product_id]
            await self._update_cart_in_redis(payload.user_id, cart)

            if not payload.notify_user:
                return

            alternatives = []
            ai_reason = "Smart Alternative"

            if self.commerce_engine and payload.action != "clear_all":
                try:
                    alternatives = await self.commerce_engine.find_genius_alternatives(
                        self.db, payload.product_id, limit=3
                    )
                except Exception as e:
                    logger.error("Genius recovery analysis failure", extra={"error": str(e)})

            if alternatives:
                best_alt = alternatives[0]
                best_alt_price = Decimal(str(getattr(best_alt, 'price', 0)))
                best_alt_rating = float(getattr(best_alt, 'rating', 0.0))

                if best_alt_rating > 4.5:
                    ai_reason = f"Users rated this {best_alt_rating}/5 ⭐"
                elif best_alt_price < item_to_remove.price:
                    diff = item_to_remove.price - best_alt_price
                    ai_reason = f"Save ${diff:.2f} with this choice 💰"
                elif best_alt_price > item_to_remove.price:
                    ai_reason = "Upgrade to the Pro version 🚀"
                else:
                    ai_reason = "A trending alternative in this category 🔥"

                response_msg = f"I noticed you dropped {item_to_remove.name}. Check this out instead:"
            else:
                response_msg = f"🗑️ Removed {item_to_remove.name}. Manifest updated."

            await self._send_to_ui(payload.user_id, {
                "content": response_msg,
                "type": "product_carousel" if alternatives else "success_text",
                "products": [p.model_dump(mode='json') for p in alternatives] if alternatives else [],
                "reason": ai_reason if alternatives else None
            })

            if cart.items:
                await asyncio.sleep(0.1)  # Minimal non-blocking jitter to ensure sequential UI rendering
                await self._send_to_ui(payload.user_id, {
                    "content": None,
                    "type": "confirmation_prompt",
                    "options": ["Confirm Order", "Keep Shopping"]
                })

            self._emit_analytics_event(
                payload.user_id,
                item_to_remove.product_id,
                "smart_recovery_triggered" if alternatives else "removal"
            )
        else:
            await self._update_cart_in_redis(payload.user_id, cart)

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

        await self.cache.delete(self._get_cart_key(payload.user_id))

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
