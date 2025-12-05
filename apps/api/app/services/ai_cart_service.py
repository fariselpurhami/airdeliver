# apps/api/app/services/ai_cart_service.py

import logging
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.models.product import Product
# [ARCHITECTURAL UPGRADE] Import Models & Enums for Type Safety
from app.models.order import Order
from app.models.enums import OrderStatus

# Define Logger
logger = logging.getLogger(__name__)

class AICartService:
    """
    Manages the volatile shopping cart state in Redis AND syncs lifecycle with SQL.
    Golden Standard: Uses Strict Enums for State Management.
    """
    def __init__(
        self,
        db: AsyncSession,
        cache: IAsyncCacheClient,
        rabbitmq: RabbitMQService,
    ):
        self.db = db
        self.cache = cache
        self.rabbitmq = rabbitmq

    def _get_cart_key(self, user_id: int) -> str:
        return f"ai_cart:{user_id}"

    async def _get_cart_from_redis(self, user_id: int) -> dict:
        cart_key = self._get_cart_key(user_id)
        cart = await self.cache.get_json(cart_key)
        if not cart:
            cart = {"items": [], "total": 0.0}
        return cart

    async def _update_cart_in_redis(self, user_id: int, cart: dict):
        cart_key = self._get_cart_key(user_id)
        total = sum(item["price"] * item["quantity"] for item in cart["items"])
        cart["total"] = round(total, 2)
        await self.cache.set_json(cart_key, cart, ttl=3600)
        
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": cart, "type": "cart_preview"},
            "airdeliver.ai.response.out",
        )

    # --- [CRITICAL LOGIC] Immediate SQL Cancellation ---
    async def delete_cart(self, user_id: int):
        """
        Hard delete of the cart. 
        ACTION: Instantly sets any PENDING SQL orders to CANCELLED using Strict Enums.
        """
        # 1. Clear Redis Cache (The Volatile State)
        cart_key = self._get_cart_key(user_id)
        await self.cache.delete(cart_key)
        
        # 2. Synchronize SQL State (The Persistent State)
        try:
            # [FIX] Use OrderStatus Enum instead of strings
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
                logger.info(f"🚫 Cleaned up {len(results)} pending orders for User {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to sync pending orders state: {e}")
        
        # 3. Push empty state to UI
        empty_cart = {"items": [], "total": 0.0}
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": empty_cart, "type": "cart_preview"},
            "airdeliver.ai.response.out",
        )

    async def handle_add_to_cart(self, payload: dict):
        user_id = payload["user_id"]
        product_id = payload["product_id"]
        quantity = payload.get("quantity", 1)

        product = await self.db.get(Product, product_id)
        if not product:
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Product unavailable.", "type": "error"},
                "airdeliver.ai.response.out",
            )
            return

        cart = await self._get_cart_from_redis(user_id)
        
        existing_item = next((item for item in cart["items"] if item["product_id"] == product_id), None)

        if existing_item:
            existing_item["quantity"] += quantity
        else:
            cart["items"].append({
                "product_id": product.id,
                "name": product.name,
                "quantity": quantity,
                "price": product.price,
                "image_url": product.image_url,
                "category": product.category
            })

        await self._update_cart_in_redis(user_id, cart)

    async def handle_remove_from_cart(self, payload: dict):
        user_id = payload["user_id"]
        product_id_to_remove = payload.get("product_id")
        action_source = payload.get("action")

        cart = await self._get_cart_from_redis(user_id)
        item_to_remove = None

        if product_id_to_remove:
            item_to_remove = next(
                (item for item in cart["items"] if str(item["product_id"]) == str(product_id_to_remove)), 
                None
            )
        else:
            product_name = payload.get("product_name", "")
            item_to_remove = next((item for item in cart["items"] if product_name.lower() in item["name"].lower()), None)

        if item_to_remove:
            cart["items"] = [
                item for item in cart["items"] 
                if str(item["product_id"]) != str(item_to_remove["product_id"])
            ]
            
            await self._update_cart_in_redis(user_id, cart)

            if action_source == "remove_by_id":
                return

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": f"Removed {item_to_remove['name']}.", "type": "success_text"},
                "airdeliver.ai.response.out",
            )

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "removed_product_id": item_to_remove["product_id"],
                    "removed_product_name": item_to_remove["name"],
                    "category": item_to_remove.get("category", "general")
                },
                "airdeliver.ai.intent.removal_recovery"
            )
        else:
            logger.warning(f"⚠️ Cart Mismatch for User {user_id}: Item {product_id_to_remove} not found.")
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "I couldn't find that item in your cart.", "type": "error"},
                "airdeliver.ai.response.out",
            )

    async def handle_clear_cart(self, payload: dict):
        user_id = payload["user_id"]
        
        # Reuse logic: Wipe Cache + Cancel SQL Order
        await self.delete_cart(user_id)

        if payload.get("notify_user", False):
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Done! Your cart is wiped clean.", "type": "success_text"},
                "airdeliver.ai.response.out",
            )
