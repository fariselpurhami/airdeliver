# apps/api/app/services/ai_nlu_service.py

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.rabbitmq_service import RabbitMQService
from app.models.product import Product
from typing import List, Dict, Any

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
        statement = select(Product).order_by(Product.rating.desc()).limit(5)
        products = (await self.db.exec(statement)).all()

        await self.rabbitmq.publish(
            {
                "user_id": user_id,
                "content": "Here are some popular items you might like:",
                "type": "proactive_suggestion",
                "products": [p.model_dump() for p in products],
                "reason": "Displaying top-rated products to start your order."
            },
            "airdeliver.ai.response.out",
        )

    async def process_message(self, message_payload: dict):
        user_id = message_payload["user_id"]
        message = message_payload["message"]

        if message == "__INTERNAL_GET_INITIAL_SUGGESTIONS__":
            await self._handle_initial_suggestions(user_id)
            return

        if message_payload.get("type") == "CANCEL_INTENT":
            await self.rabbitmq.publish(
                {"user_id": user_id, "order_id": message.get("orderId")},
                "airdeliver.ai.intent.cancel_order",
            )
            return

        products, entities = await self.search_engine.find_products_from_message(
            db=self.db, message=message, user_id=user_id
        )

        intent = entities.get("intent", "SEARCH_PRODUCT")

        response_payload = {"user_id": user_id, "original_message": message}

        if intent == "ADD_TO_CART":
            if not products:
                await self.rabbitmq.publish(
                    {**response_payload, "content": f"I couldn't find '{message}'.", "type": "error"},
                    "airdeliver.ai.response.out",
                )
            elif len(products) > 1:
                await self.rabbitmq.publish(
                    {**response_payload, "products": [p.model_dump() for p in products], "type": "clarify"},
                    "airdeliver.ai.response.out",
                )
            else:
                await self.rabbitmq.publish(
                    {**response_payload, "product_id": products[0].id, "quantity": entities.get("quantity", 1)},
                    "airdeliver.ai.intent.add_to_cart",
                )

        elif intent == "REMOVE_FROM_CART":
            await self.rabbitmq.publish(
                {**response_payload, "product_name": message},
                "airdeliver.ai.intent.remove_from_cart",
            )

        elif intent == "CONFIRM_ORDER":
             await self.rabbitmq.publish(
                {**response_payload, **message_payload},
                "airdeliver.ai.intent.confirm_order",
            )

        elif intent == "SEARCH_PRODUCT":
            if products:
                await self.rabbitmq.publish(
                    {
                        **response_payload,
                        "content": "Here is what I found based on your search:",
                        "type": "product_carousel",
                        "products": [p.model_dump() for p in products]
                    },
                    "airdeliver.ai.response.out",
                )
            else:
                await self.rabbitmq.publish(
                    {**response_payload, "content": "I'm not sure what you mean or I couldn't find that item.", "type": "error"},
                    "airdeliver.ai.response.out",
                )
        else:
             await self.rabbitmq.publish(
                {**response_payload, "content": "I'm not sure what you mean.", "type": "error"},
                "airdeliver.ai.response.out",
            )
