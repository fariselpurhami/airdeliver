# apps/api/app/services/ai_cart_service.py

from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService
from app.models.product import Product
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

class AICartService:
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
        cart["total"] = total
        await self.cache.set_json(cart_key, cart, ttl=3600)
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": cart, "type": "cart_preview"},
            "airdeliver.ai.response.out",
        )

    async def handle_add_to_cart(self, payload: dict):
        user_id = payload["user_id"]
        product_id = payload["product_id"]
        quantity = payload["quantity"]

        product = await self.db.get(Product, product_id)
        if not product:
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Product not found.", "type": "error"},
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
            })

        await self._update_cart_in_redis(user_id, cart)

    async def handle_remove_from_cart(self, payload: dict):
        user_id = payload["user_id"]
        product_id_to_remove = payload.get("product_id")

        cart = await self._get_cart_from_redis(user_id)

        item_to_remove = None

        if product_id_to_remove:
            item_to_remove = next((item for item in cart["items"] if item["product_id"] == product_id_to_remove), None)
        else:
            product_name = payload.get("product_name", "")
            item_to_remove = next((item for item in cart["items"] if product_name.lower() in item["name"].lower()), None)


        if item_to_remove:
            cart["items"] = [item for item in cart["items"] if item["product_id"] != item_to_remove["product_id"]]

            await self.rabbitmq.publish(
                {"user_id": user_id, "content": f"Removed {item_to_remove['name']} from cart successfully!", "type": "success_text"},
                "airdeliver.ai.response.out",
            )
            await self._update_cart_in_redis(user_id, cart)
        else:
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": f"Couldn't find item to remove.", "type": "error"},
                "airdeliver.ai.response.out",
            )

    async def handle_clear_cart(self, payload: dict):
        user_id = payload["user_id"]
        cart_key = self._get_cart_key(user_id)
        
        await self.cache.delete(cart_key)
        
        empty_cart = {"items": [], "total": 0.0}
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": empty_cart, "type": "cart_preview"},
            "airdeliver.ai.response.out",
        )
        
        if payload.get("notify_user", False):
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Cart cleared successfully.", "type": "success_text"},
                "airdeliver.ai.response.out",
            )
