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

    async def _send_add_success_prompt(self, user_id: int, product_name: str):
        # 1. إرسال رسالة نص النجاح (Great! I've added...)
        await self.rabbitmq.publish(
            {
                "user_id": user_id,
                "content": f"Great! I've added {product_name} to your cart.",
                "type": "success_text"
            },
            "airdeliver.ai.response.out",
        )

        # 2. إرسال طلب التأكيد (Confirm Order / Clear Cart)
        await self.rabbitmq.publish(
            {
                "user_id": user_id,
                "content": "Shall we confirm the order or clear the cart?",
                "type": "confirmation_prompt",
                "options": ["Confirm Order", "Clear Cart"],
            },
            "airdeliver.ai.response.out",
        )

    async def _handle_initial_suggestions(self, user_id: int):
        # هذا المنطق مخصص للاقتراحات الأولية (Initial Suggestions)
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

        # -----------------------------------------------------
        # 💡 إصلاح 1: معالجة الأوامر الداخلية والعودة المبكرة (Early Return)
        # -----------------------------------------------------
        if message == "__INTERNAL_GET_INITIAL_SUGGESTIONS__":
            await self._handle_initial_suggestions(user_id)
            return

        if message.startswith("__INTERNAL_ADD_BY_ID__:") and user_id:
            try:
                product_id_str = message.split(":")[1]
                product_id = int(product_id_str)

                # إرسال الأمر لخدمة السلة
                await self.rabbitmq.publish(
                    {"user_id": user_id, "product_id": product_id, "quantity": 1},
                    "airdeliver.ai.intent.add_to_cart",
                )

                # إرسال الرد المتوقع مباشرة (لتفادي التعليق)
                product = await self.db.get(Product, product_id)
                if product:
                    await self._send_add_success_prompt(user_id, product.name)

                return # 👈 الأهم: إنهاء التنفيذ ومنع الوصول إلى محرك البحث المنهار
            except Exception as e:
                await self.rabbitmq.publish(
                    {"user_id": user_id, "content": f"Error adding item: {e}", "type": "error"},
                    "airdeliver.ai.response.out",
                )
                return # 👈 إنهاء التنفيذ عند الفشل

        if message_payload.get("type") == "CANCEL_INTENT":
            await self.rabbitmq.publish(
                {"user_id": user_id, "order_id": message.get("orderId")},
                "airdeliver.ai.intent.cancel_order",
            )
            return

        # -----------------------------------------------------
        # ⚠️ منطق البحث (يتم تنفيذه فقط إذا لم يكن الأمر داخليًا)
        # -----------------------------------------------------
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
                    {**response_payload, "content": "I couldn't find that item.", "type": "error"},
                    "airdeliver.ai.response.out",
                )
        else:
             await self.rabbitmq.publish(
                {**response_payload, "content": "I'm not sure what you mean.", "type": "error"},
                "airdeliver.ai.response.out",
            )
