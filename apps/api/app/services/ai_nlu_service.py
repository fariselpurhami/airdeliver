# apps/api/app/services/ai_nlu_service.py

import logging
import random
import json
from typing import List, Dict, Any, Optional, Set
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import IAsyncCacheClient
from app.models.product import Product

logger = logging.getLogger(__name__)

class AINLUService:
    def __init__(
        self,
        db: AsyncSession,
        search_engine: AICommerceEngine,
        rabbitmq: RabbitMQService,
        cache: IAsyncCacheClient,
    ):
        self.db = db
        self.search_engine = search_engine
        self.rabbitmq = rabbitmq
        self.cache = cache
        self.seen_cache_ttl = 3600

    def _get_seen_key(self, user_id: int) -> str:
        return f"ai_session:{user_id}:seen_products"

    async def _get_seen_product_ids(self, user_id: int) -> Set[int]:
        key = self._get_seen_key(user_id)
        try:
            members = await self.cache.smembers(key)
            return {int(m) for m in members} if members else set()
        except Exception:
            return set()

    async def _mark_products_as_seen(self, user_id: int, products: List[Dict[str, Any]]):
        if not products: return
        key = self._get_seen_key(user_id)
        ids = [str(p['id']) for p in products]
        try:
            await self.cache.sadd(key, *ids)
            await self.cache.expire(key, self.seen_cache_ttl)
        except Exception: pass

    async def _get_global_backup_products(self) -> List[Dict[str, Any]]:
        cache_key = "global:trending_products:v1"
        cached_products = await self.cache.get_json(cache_key)

        if cached_products:
            return cached_products

        statement = select(Product).order_by(Product.rating.desc()).limit(200)
        products = (await self.db.exec(statement)).all()

        if products:
            products_data = [p.model_dump(mode='json') for p in products]
            await self.cache.set_json(cache_key, products_data, ttl=600)
            return products_data

        return []

    async def _filter_candidates(self, user_id: int, candidates: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        seen_ids = await self._get_seen_product_ids(user_id)
        fresh_candidates = [p for p in candidates if p['id'] not in seen_ids]

        if len(fresh_candidates) >= limit:
            return random.sample(fresh_candidates, limit)

        if fresh_candidates:
            return fresh_candidates

        return []

    async def _handle_initial_suggestions(self, user_id: int):
        backup_pool = await self._get_global_backup_products()
        final_selection = await self._filter_candidates(user_id, backup_pool, limit=10)

        if not final_selection:
            await self.cache.delete(self._get_seen_key(user_id))
            final_selection = random.sample(backup_pool, min(len(backup_pool), 10)) if backup_pool else []

        if final_selection:
            await self._mark_products_as_seen(user_id, final_selection)
            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Welcome! Here are the top trending items tailored for you:",
                    "type": "proactive_suggestion",
                    "products": final_selection,
                    "reason": "Global trending items selected for you."
                },
                "airdeliver.ai.response.out",
            )

    async def _handle_secondary_suggestions(self, user_id: int, added_product: Product):
        final_products = []
        suggestion_reason = ""

        try:
            complementary_products = await self.search_engine.find_complementary_products(
                db=self.db, anchor_product=added_product, limit=20
            )
            complementary_data = [p.model_dump(mode='json') for p in complementary_products]
            final_products = await self._filter_candidates(user_id, complementary_data, limit=5)

            if final_products:
                suggestion_reason = f"Perfect matches for your **{added_product.name}**:"
        except Exception as e:
            logger.error(f"Semantic search error: {e}")

        if len(final_products) < 5:
            backup_pool = await self._get_global_backup_products()
            needed = 5 - len(final_products)

            backup_candidates = await self._filter_candidates(user_id, backup_pool, limit=50)
            unique_backups = [p for p in backup_candidates if p['id'] not in {x['id'] for x in final_products}]

            fillers = unique_backups[:needed]
            final_products.extend(fillers)

            if not suggestion_reason:
                suggestion_reason = "You might also like these popular picks:"

        if not final_products:
            statement = select(Product).where(Product.id != added_product.id).order_by(func.random()).limit(5)
            emergency_products = (await self.db.exec(statement)).all()
            final_products = [p.model_dump(mode='json') for p in emergency_products]
            suggestion_reason = "Discover more form our collection:"

        if final_products:
            await self._mark_products_as_seen(user_id, final_products)
            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": suggestion_reason,
                    "type": "proactive_suggestion",
                    "products": final_products,
                    "reason": "Smart curation based on your cart."
                },
                "airdeliver.ai.response.out",
            )

    async def _send_add_success_text(self, user_id: int, product_name: str):
        success_messages = [
            f"**{product_name}** added! 🚀 Excellent choice.",
            f"**{product_name}** added! ✨ This will look great.",
            f"**{product_name}** added! 📦 Secured in your cart.",
        ]
        selected_content = random.choice(success_messages)
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": selected_content, "type": "success_text"},
            "airdeliver.ai.response.out",
        )

    async def _send_confirmation_prompt(self, user_id: int):
        await self.rabbitmq.publish(
            {
                "user_id": user_id,
                "content": "I'm ready when you are. Proceed to checkout?",
                "type": "confirmation_prompt",
                "options": ["Confirm Order", "Clear Cart"],
            },
            "airdeliver.ai.response.out",
        )

    async def _handle_add_to_cart_success(self, user_id: int, product: Product):
        await self._send_add_success_text(user_id, product.name)
        await self._handle_secondary_suggestions(user_id, product)
        await self._send_confirmation_prompt(user_id)

    async def process_message(self, message_payload: dict):
        user_id = message_payload.get("user_id")
        raw_message = message_payload.get("message")

        if isinstance(raw_message, dict):
             message_text = ""
        else:
             message_text = str(raw_message).strip() if raw_message else ""

        if not raw_message: return

        if message_text.startswith("__INTERNAL_"):
            await self._process_internal_command(user_id, message_text)
            return

        lower_msg = message_text.lower()
        if lower_msg in ["confirm order", "confirm", "checkout"]:
            await self.rabbitmq.publish(
                {**message_payload, "user_id": user_id},
                "airdeliver.ai.intent.confirm_order",
            )
            return

        if lower_msg in ["clear cart", "empty cart"]:
            await self.rabbitmq.publish(
                {"user_id": user_id, "notify_user": True},
                "airdeliver.ai.intent.clear_cart",
            )
            return

        if message_payload.get("type") == "CANCEL_INTENT":
            order_id = None
            reason = None
            if isinstance(raw_message, dict):
                order_id = raw_message.get("orderId") or raw_message.get("order_id")
                reason = raw_message.get("reason")
            await self.rabbitmq.publish({"user_id": user_id, "order_id": order_id, "reason": reason}, "airdeliver.ai.intent.cancel_order")
            return

        try:
            products, entities = await self.search_engine.find_products_from_message(
                db=self.db, message=message_text, user_id=user_id
            )
        except Exception as e:
            logger.error(f"Search Engine Critical Failure: {e}", exc_info=True)
            products, entities = ([], {"intent": "SEARCH_PRODUCT"})

        intent = entities.get("intent", "SEARCH_PRODUCT")
        response_payload = {"user_id": user_id, "original_message": message_text}

        if intent == "ADD_TO_CART":
            if not products:
                 await self.rabbitmq.publish({
                        **response_payload,
                        "content": f"I couldn't find exactly '{message_text}', but check these out:",
                        "type": "product_carousel",
                        "products": []
                    }, "airdeliver.ai.response.out")
            elif len(products) > 1:
                 await self.rabbitmq.publish({
                        **response_payload,
                        "content": f"I found a few items matching '{message_text}'. Which one?",
                        "type": "proactive_suggestion",
                        "products": [p.model_dump(mode='json') for p in products[:10]]
                    }, "airdeliver.ai.response.out")
            else:
                added_product = products[0]
                await self.rabbitmq.publish({**response_payload, "product_id": added_product.id, "quantity": 1}, "airdeliver.ai.intent.add_to_cart")
                await self._handle_add_to_cart_success(user_id, added_product)

        elif intent == "SEARCH_PRODUCT":
            if products:
                intro_text = "Found these for you:"
                if "wedding" in lower_msg: intro_text = "Looking sharp! Here are some elegant options:"
                if "iphone" in lower_msg: intro_text = "Here are the latest models and accessories:"

                await self.rabbitmq.publish({
                    **response_payload,
                    "content": intro_text,
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in products]
                }, "airdeliver.ai.response.out")
            else:
                await self.rabbitmq.publish({**response_payload, "content": f"I couldn't find anything matching '{message_text}'. Try generic terms like 'phones' or 'shoes'.", "type": "error"}, "airdeliver.ai.response.out")

    async def _process_internal_command(self, user_id: int, command: str):
        if command == "__INTERNAL_SAVE_FOR_LATER__":
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Got it 💾, saved to your wishlist.", "type": "success_text"},
                "airdeliver.ai.response.out",
            )
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": False}, "airdeliver.ai.intent.clear_cart")
            return

        if command == "__INTERNAL_GET_INITIAL_SUGGESTIONS__":
            await self._handle_initial_suggestions(user_id)
            return

        if command == "__INTERNAL_RESET_SESSION__":
            await self.cache.delete(self._get_seen_key(user_id))
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": False}, "airdeliver.ai.intent.clear_cart")
            return

        if command == "__INTERNAL_CLEAR_CART__":
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": True}, "airdeliver.ai.intent.clear_cart")
            return

        if command.startswith("__INTERNAL_ADD_BY_ID__:") and user_id:
            try:
                product_id = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": product_id, "quantity": 1}, "airdeliver.ai.intent.add_to_cart")
                product = await self.db.get(Product, product_id)
                if product:
                    await self._handle_add_to_cart_success(user_id, product)
            except Exception: pass
            return

        if command.startswith("__INTERNAL_REMOVE_BY_ID__:") and user_id:
            try:
                product_id = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": product_id, "action": "remove_by_id"}, "airdeliver.ai.intent.remove_from_cart")
            except Exception: pass
            return
