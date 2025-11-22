# //** apps/api/app/services/ai_nlu_service.py **//

import logging
import random
import asyncio
from typing import List, Dict, Any, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.rabbitmq_service import RabbitMQService
from app.models.product import Product

logger = logging.getLogger(__name__)

class AINLUService:

    def __init__(
        self,
        db: AsyncSession,
        search_engine: AICommerceEngine,
        rabbitmq: RabbitMQService,
    ):
        self.db = db
        self.search_engine = search_engine
        self.rabbitmq = rabbitmq

    async def _handle_initial_suggestions(self, user_id: int):
        
        statement = select(Product).order_by(Product.rating.desc()).limit(20)
        products = (await self.db.exec(statement)).all()
        
        if products:
    
            selected = random.sample(products, min(len(products), 10))
            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "content": "Here are the top picks trending worldwide right now:",
                    "type": "proactive_suggestion",
                    "products": [p.model_dump() for p in selected],
                    "reason": "Global trending items selected for you."
                },
                "airdeliver.ai.response.out",
            )

    async def _send_add_success_text(self, user_id: int, product_name: str):
        success_messages = [
            f"**{product_name}** added! 🚀 You've got great taste.",
            f"**{product_name}** added! ✨ Smooth and sharp selection.",
            f"**{product_name}** added! 💎 Perfect choice that one never disappoints.",
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
                "content": "Systems ready. Move to checkout?",
                "type": "confirmation_prompt",
                "options": ["Confirm Order", "Clear Cart"],
            },
            "airdeliver.ai.response.out",
        )
        
    async def _handle_secondary_suggestions(self, user_id: int, added_product: Product):
        
        try:
            products = await self.search_engine.find_complementary_products(
                db=self.db, anchor_product=added_product, limit=5
            )
            if products:
                await self.rabbitmq.publish(
                    {
                        "user_id": user_id,
                        "content": f"People who bought **{added_product.name}** also loved these:",
                        "type": "proactive_suggestion",
                        "products": [p.model_dump() for p in products],
                        "reason": f"Curated matching items just for you."
                    },
                    "airdeliver.ai.response.out",
                )
        except Exception as e:
            logger.error(f"Secondary suggestion failed: {e}")
            
    async def _handle_add_to_cart_success(self, user_id: int, product: Product):
        
        await self._send_add_success_text(user_id, product.name)
        await self._send_confirmation_prompt(user_id)
        await self._handle_secondary_suggestions(user_id, product)

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
                 # Ambiguity Resolution
                 await self.rabbitmq.publish({
                        **response_payload,
                        "content": f"I found a few items matching '{message_text}'. Which one?",
                        "type": "proactive_suggestion",
                        "products": [p.model_dump() for p in products[:10]]
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
                    "products": [p.model_dump() for p in products] 
                }, "airdeliver.ai.response.out")
            else:
                await self.rabbitmq.publish({**response_payload, "content": f"I couldn't find anything matching '{message_text}'. Try generic terms like 'phones' or 'shoes'.", "type": "error"}, "airdeliver.ai.response.out")

    async def _process_internal_command(self, user_id: int, command: str):
        """Handles system commands securely"""
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
            except Exception: 
                pass
            return

        if command.startswith("__INTERNAL_REMOVE_BY_ID__:") and user_id:
            try:
                product_id = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": product_id, "action": "remove_by_id"}, "airdeliver.ai.intent.remove_from_cart")
            except Exception: 
                pass
            return
