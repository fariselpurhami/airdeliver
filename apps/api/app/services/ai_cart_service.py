# apps/api/app/services/ai_cart_service.py

import logging
import json
import random
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.models.product import Product
from app.services.ai_commerce_engine import AICommerceEngine
from app.models.order import Order
from app.models.enums import OrderStatus, CancellationReason

logger = logging.getLogger("airdeliver.cart")

class AICartService:
    """
    🛒 DIAMOND CART SERVICE (V4.0 - UNIVERSAL EDITION).

    The Intelligent Sales Agent that manages the user's shopping manifest.
    It acts as a high-speed buffer between the User and the Checkout.

    ARCHITECTURAL PILLARS:
    1. ⚡ RAM-Speed State: Uses Redis as the primary source of truth.
    2. �� Vector Bundling: Mathematical calculation of complementary products.
    3. 🛡️ Semantic Recovery: Prevents cart abandonment.
    4. 🔌 Real-Time Uplink: Websocket-ready JSON payloads via Redis Pub/Sub.
    """

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
        self.commerce_engine = commerce_engine # 💎 The Brain Injection

    # --- 🔌 1. UI RESPONSE ROUTER (FERRARI SPEED) ---
    async def _send_to_ui(self, user_id: int, payload: dict):
        """
        Sends formatted JSON payloads directly to the Frontend WebSocket via Redis.
        Includes a 'Universal Serializer' to handle Decimals and Datetimes safely.
        """
        try:
            channel = f"airdeliver:response:{user_id}"

            # Metadata for frontend tracking
            payload["meta"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "ai_cart_v4"
            }

            # 🛡️ Universal Serializer: The Shield against JSON Errors
            def safe_serializer(obj):
                if hasattr(obj, 'isoformat'): return obj.isoformat()
                if hasattr(obj, '__str__'): return str(obj) # Handles Decimal
                return None

            message = json.dumps(payload, default=safe_serializer)
            await self.cache.publish(channel, message)
        except Exception as e:
            logger.error(f"🔥 UI Delivery Failed in CartService: {e}")

    # --- 🛠️ 2. REDIS CART HELPERS (STATE MANAGEMENT) ---
    def _get_cart_key(self, user_id: int) -> str:
        return f"ai_cart:{str(user_id)}"

    async def _get_cart_from_redis(self, user_id: int) -> dict:
        """Retrieves cart state from RAM. Returns empty structure if missing."""
        try:
            cart = await self.cache.get_json(self._get_cart_key(user_id))
            return cart if cart else {"items": [], "total": 0.0}
        except Exception:
            return {"items": [], "total": 0.0}

    async def _update_cart_in_redis(self, user_id: int, cart: dict):
        """
        Calculates totals and persists state.
        CRITICAL: Converts all prices to Float to avoid Decimal serialization errors.
        """
        try:
            # 1. Recalculate Total Live (Safe Float Conversion)
            total = sum(float(item["price"]) * int(item["quantity"]) for item in cart["items"])
            cart["total"] = round(total, 2)
            cart["updated_at"] = datetime.utcnow().isoformat()

            # 2. Persist to RAM (TTL: 24 Hours)
            await self.cache.set_json(self._get_cart_key(user_id), cart, ttl=86400)

            # 3. Push Live Update to UI
            await self._send_to_ui(user_id, {
                "content": cart,
                "type": "cart_preview",
                "reason": "State Sync"
            })
        except Exception as e:
            logger.error(f"Redis Cart Update Failed: {e}")

    # --- ➕ 3. HANDLE ADD TO CART (WITH SMART BUNDLING) ---
    async def handle_add_to_cart(self, payload: dict):
        """
        Adds item -> Updates Redis -> Triggers Vector Bundle Engine.
        """
        user_id = payload.get("user_id")
        product_id = payload.get("product_id")
        quantity = payload.get("quantity", 1)
        notify_user = payload.get("notify_user", True) # Silent mode for internal ops

        # A. Validation
        product = await self.db.get(Product, product_id)
        if not product:
            if notify_user:
                await self._send_to_ui(user_id, {"content": "Product unavailable or out of stock.", "type": "error"})
            return

        # B. Update Redis State
        cart = await self._get_cart_from_redis(user_id)

        # Check if item exists (String comparison for safety)
        existing_item = next((item for item in cart["items"] if str(item["product_id"]) == str(product_id)), None)

        if existing_item:
            existing_item["quantity"] += quantity
        else:
            # 🛡️ Safe Extraction using getattr + Float Conversion
            cart["items"].append({
                "product_id": product.id,
                "name": product.name,
                "quantity": quantity,
                "price": float(product.price), # Ensure Float for JSON
                "image_url": getattr(product, 'image_url', ''),
                "category": getattr(product, 'category', '')
            })

        await self._update_cart_in_redis(user_id, cart)

        # C. Instant User Feedback
        if notify_user:
            await self._send_to_ui(user_id, {
                "content": f" {product.name} secured in manifest.",
                "type": "success_text"
            })

        # D. 💎 INTELLIGENT BUNDLING (The Upsell)
        # Only trigger if commerce engine is injected & user needs notification
        if self.commerce_engine and notify_user:
            try:
                # 1. Ask the Brain for complementary items (Vector Arithmetic)
                bundle_items = await self.commerce_engine.generate_perfect_bundle(self.db, product)

                if bundle_items:
                    reasons = [
                        f"People who bought {product.name} usually grab these too:",
                        f"Complete your setup! Essentials for your {product.name}:",
                        "I selected these accessories to match your new item perfectly:",
                        f"Enhance your {product.name} experience with these:"
                    ]

                    await self._send_to_ui(user_id, {
                        "content": random.choice(reasons),
                        "type": "product_carousel",
                        "products": [p.model_dump(mode='json') for p in bundle_items], # 🛡️ Safe Dump
                        "secondary_suggestions": True, # UI Hint
                        "reason": "Smart Ecosystem Bundle"
                    })
            except Exception as e:
                logger.warning(f"Bundling Logic Warning: {e}")

        # E. Checkout Prompt (Nudge)
        if notify_user:
            await self._send_to_ui(user_id, {
                "content": "Ready to checkout or keep exploring?",
                "type": "confirmation_prompt",
                "options": ["Confirm Order", "Keep Shopping"]
            })
    # --- 💾 6. HANDLE SAVE FOR LATER ---
    async def handle_save_cart(self, payload: dict):
        """
        Persists the Redis Cart to SQL as a 'Saved' Order, then clears Redis.
        """
        user_id = payload.get("user_id")
        
        # 1. Get Redis Cart
        cart = await self._get_cart_from_redis(user_id)
        if not cart or not cart.get("items"):
            await self._send_to_ui(user_id, {"content": "Nothing to save.", "type": "error"})
            return

        try:
            from app.models.order import Order, OrderItem, OrderStatus, CancellationReason
            
            # 2. Create 'Saved' Order in DB
            # We use CANCELLED status with a special reason 'SAVED_FOR_LATER' 
            # Or use PENDING if you have a specific flow. Here we mimic 'Discard' logic but positive.
            
            # حساب الإجمالي
            total_amount = cart.get("total", 0.0)
            
            saved_order = Order(
                user_id=user_id,
                status=OrderStatus.CANCELLED, # أو PENDING لو عايز تظهرها بشكل مختلف
                cancellation_reason=CancellationReason.CHANGED_MIND, # أو SAVED لو ضفتها للـ Enum
                total_price=total_amount,
                delivery_address="Saved List",
                created_at=datetime.utcnow()
            )
            self.db.add(saved_order)
            await self.db.flush()

            # حفظ العناصر
            for item in cart["items"]:
                self.db.add(OrderItem(
                    order_id=saved_order.id,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price_per_unit=float(item["price"])
                ))
            
            await self.db.commit()

            # 3. Wipe Redis (Like Clear Cart)
            await self.cache.delete(self._get_cart_key(user_id))

            # 4. Notify UI (This unfreezes the frontend)
            await self._send_to_ui(user_id, {
                "content": "Manifest archived securely. You can restore it from your profile.",
                "type": "success_text"
            })
            
            # Send empty cart to clear sidebar
            await self._send_to_ui(user_id, {
                "content": {"items": [], "total": 0.0},
                "type": "cart_preview"
            })

        except Exception as e:
            logger.error(f"Save Cart Failed: {e}")
            await self._send_to_ui(user_id, {"content": "Failed to save cart.", "type": "error"})

    async def handle_remove_from_cart(self, payload: dict):
        """
        Removes item -> Analyzes Intent -> Suggests Better Alternatives.
        The goal is to turn a 'Negative Action' (Removal) into a 'Positive Conversion'.
        """
        user_id = payload.get("user_id")
        product_id_to_remove = payload.get("product_id")
        action_type = payload.get("action", "manual_remove")
        
        notify_user = payload.get("notify_user", True)
        # 1. Get Current State
        cart = await self._get_cart_from_redis(user_id)
        
        # Find item before removing (to get name/price for logic)
        # Using str() for ID comparison to be safe
        item_to_remove = next((item for item in cart["items"] if str(item["product_id"]) == str(product_id_to_remove)), None)
        
        if item_to_remove:
            # A. Execute Removal in Redis
            cart["items"] = [item for item in cart["items"] if str(item["product_id"]) != str(item_to_remove["product_id"])]
            await self._update_cart_in_redis(user_id, cart)
            
            if not notify_user:
                return
            removed_name = item_to_remove['name']
            # Safe Float Conversion for Math
            removed_price = float(item_to_remove['price'])
            
            # B. 💎 GENIUS RECOVERY: Find the Perfect Alternative
            alternatives = []
            ai_reason = "Smart Alternative" 
            
            # Only attempt recovery if manual removal (not clearing cart)
            # And if we have the Commerce Engine injected
            if self.commerce_engine and action_type != "clear_all":
                try:
                    # Use the new Vector Pivot function (Semantic Pivot)
                    # This finds items similar to the removed one, but potentially better
                    alternatives = await self.commerce_engine.find_genius_alternatives(
                        self.db, int(product_id_to_remove), limit=3
                    )
                except Exception as e:
                    logger.warning(f"Genius Recovery Failed: {e}")

            # C. 🧠 INTELLIGENT COPYWRITING (Smart Comparison)
            if alternatives:
                best_alt = alternatives[0]
                # Safe Attribute Access
                best_alt_price = float(getattr(best_alt, 'price', 0))
                best_alt_rating = float(getattr(best_alt, 'rating', 0))
                
                # Logic to generate "Genius Reason"
                if best_alt_rating > 4.5:
                    ai_reason = f"Users rated this {best_alt_rating}/5 ⭐"
                elif best_alt_price < removed_price:
                    diff = removed_price - best_alt_price
                    ai_reason = f"Save ${diff:.2f} with this choice 💰"
                elif best_alt_price > removed_price:
                    ai_reason = "Upgrade to the Pro version 🚀"
                else:
                    ai_reason = "A trending alternative in this category 🔥"

                response_msg = f"I noticed you dropped {removed_name}. Check this out instead:"
            else:
                response_msg = f"🗑️ Removed {removed_name}. Manifest updated."

            await self._send_to_ui(user_id, {
                "content": response_msg,
                "type": "product_carousel" if alternatives else "success_text",
                "products": [p.model_dump(mode='json') for p in alternatives] if alternatives else [], # 🛡️ Safe Dump
                "reason": ai_reason if alternatives else None
            })
            
            # E. Analytics (Async Fire-and-Forget)
            try:
                await self.rabbitmq.publish(
                    {
                        "user_id": user_id,
                        "removed_product_id": item_to_remove["product_id"],
                        "action": "smart_recovery_triggered" if alternatives else "removal",
                        "timestamp": datetime.utcnow().timestamp()
                    },
                    "airdeliver.ai.intent.removal_recovery"
                )
            except: pass

        else:
            # Fallback sync if item somehow missing in finding logic but present in key
            await self._update_cart_in_redis(user_id, cart)
    # --- 🧹 5. HANDLE CLEAR CART (HARD RESET) ---
    async def handle_clear_cart(self, payload: dict):
        """
        Instant Wipe & Cleanup.
        Removes Redis Key AND cancels pending DB orders to ensure consistency.
        """
        user_id = payload.get("user_id")
        
        # A. Wipe Redis Key
        cart_key = self._get_cart_key(user_id)
        await self.cache.delete(cart_key)
        
        # B. Cancel Pending DB Orders (Cleanup)
        # We assume Order & OrderStatus are available, otherwise we skip
        try:
            # Dynamic Import to avoid circular dependencies if models are mixed
            from app.models.order import Order, OrderStatus
            
            statement = select(Order).where(
                Order.user_id == user_id, 
                Order.status == OrderStatus.PENDING
            )
            results = (await self.db.exec(statement)).all()
            
            if results:
                for order in results:
                    order.status = OrderStatus.CANCELLED
                    self.db.add(order)
                await self.db.commit()
                logger.info(f"🚫 Cancelled {len(results)} pending orders for User {user_id}")
        except Exception as e:
            logger.warning(f"Order Cleanup Skip: {e}")

        # C. Update UI to Empty State
        empty_cart = {"items": [], "total": 0.0}
        await self._send_to_ui(user_id, {
            "content": empty_cart, 
            "type": "cart_preview",
            "reason": "Clear Command"
        })
        
        # D. Optional Notification
        if payload.get("notify_user", False):
            await self._send_to_ui(user_id, {"content": "Cart cleared.", "type": "success_text"})
