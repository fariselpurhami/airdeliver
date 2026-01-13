# apps/api/app/services/neural_core_service.py

import logging
import json
import os
from typing import Dict, Any, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends
from groq import AsyncGroq  # 👈 التعديل الصحيح: استخدام مكتبة Groq الأصلية

from app import models
from app.services.cache_service import IAsyncCacheClient, get_cache_client
from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
from app.schemas.ai_actions import (
    NeuralCoreResponse,
    TrackOrderAction,
    SupportHandoffAction,
)

logger = logging.getLogger("airdeliver.neural_core")

class NeuralCoreService:
    """
    💎 DIAMOND STANDARD NEURAL CORE (V8.2 - Native Groq Edition).
    
    The Brain of 'Air Intelligence'.
    - POWERED BY: Llama 3.1 70B Instruct (via Native Groq Client).
    - ARCHITECTURE: Semantic Router + Empathetic Persona.
    - CAPABILITY: Context-aware routing, JSON reasoning, and fluid conversation.
    """

    def __init__(
        self,
        ai_engine: AICommerceEngine,
        cache: IAsyncCacheClient,
    ):
        self.ai_engine = ai_engine
        self.cache = cache
        self.session_ttl = 3600
        
        # ⚡ Direct Native Groq Connection
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            logger.warning("⚠️ GROQ_API_KEY is missing! Neural Core running in fallback mode.")
            self.client = None
        else:
            # استخدام عميل Groq الأصلي
            self.client = AsyncGroq(
                api_key=self.groq_api_key,
            )
        
        # Llama 3.1 70B Versatile on Groq
        self.MODEL_NAME = "llama-3.3-70b-versatile" 

    async def _get_session_key(self, session_id: str) -> str:
        return f"ai_session_v8:{session_id}"

    async def _get_context(self, session_id: str, user_name: str) -> Dict[str, Any]:
        """Retrieves conversation history to maintain 'Friendship Memory'."""
        key = await self._get_session_key(session_id)
        data = await self.cache.get_json(key)
        if not data:
            data = {"history": [], "user_name": user_name}
        return data

    async def _save_context(self, session_id: str, context: Dict[str, Any], user_msg: str, ai_msg: str):
        """Updates memory. Keeps only last 10 turns to save tokens."""
        context["history"].append({"role": "user", "content": user_msg})
        context["history"].append({"role": "assistant", "content": ai_msg})
        if len(context["history"]) > 10:
            context["history"] = context["history"][-10:]
        await self.cache.set_json(await self._get_session_key(session_id), context, ttl=self.session_ttl)

    async def _semantic_router(self, message: str, history: list) -> Dict[str, Any]:
        """
        🧠 THE BRAIN: Llama 3.1 70B Reasoning Engine.
        Decides intent with high precision using Native Groq.
        """
        if not self.client:
            return {"intent": "SOCIAL", "response": "System offline."}

        system_prompt = """
        You are the hidden cognitive router for 'Air Intelligence'.
        Analyze the user's message and history. Output a valid JSON object ONLY.
        
        Possible Intents:
        1. "PRODUCT_SEARCH": User wants to buy, check price, stock, or find items. Extract 'query'.
        2. "TRACK_ORDER": User asks about order status/location. Extract 'order_id' if present (digits only).
        3. "SUPPORT_HANDOFF": User is angry, wants a human, or has a complex issue.
        4. "SOCIAL_CHAT": General conversation, greeting, feelings, or vague questions.
        
        JSON Format:
        {
            "intent": "INTENT_NAME",
            "query": "search term if needed",
            "order_id": "12345 or null",
            "social_reply": "Generate a warm, friendly, witty reply here IF intent is SOCIAL_CHAT"
        }
        
        NOTE: For SOCIAL_CHAT, be a best friend. Witty, empathetic, use emojis. 
        User is NOT a customer, they are your 'Bestie'.
        """

        try:
            completion = await self.client.chat.completions.create(
                model=self.MODEL_NAME,
                messages=[{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}],
                temperature=0.0, # Zero temp for strict logic
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            logger.error(f"Router Error: {e}")
            return {"intent": "SOCIAL_CHAT", "social_reply": "I'm having a little brain freeze 🧊 but I'm still here with you!"}

    async def _generate_product_response(self, products: list) -> str:
        """Friendly product presentation."""
        if not products:
            return "Oof, I dug through the entire warehouse but couldn't find exactly that. 🕵️‍♂️ Want to try a different name?"
        
        top_product = products[0]
        status = "ready to ship! 🚀" if top_product.inventory > 0 else "currently out of stock 🥺"
        return f"Found it! The **{top_product.name}** is looking amazing. It's going for **${top_product.price}** and it's {status}. Shall we add it to your haul?"

    async def handle_message(
        self, 
        db: AsyncSession, 
        message: str, 
        user: Optional[models.User], 
        session_id: str
    ) -> NeuralCoreResponse:
        
        user_name = user.full_name if user else "Friend"
        context = await self._get_context(session_id, user_name)
        
        # 1. 🧠 The Router Decision (Native Groq Llama 3.1)
        decision = await self._semantic_router(message, context["history"])
        intent = decision.get("intent", "SOCIAL_CHAT")
        
        logger.info(f"�� Neural Router (Groq) | User: {user_name} | Intent: {intent}")

        response = NeuralCoreResponse(
            text="",
            confidence=0.95,
            explain=f"Processed via Native Groq ({intent})",
            telemetry={
                "intent": intent,
                "entities": [],  # ✅ Fix: Added required field
                "turn": len(context["history"]) // 2
            }
        )

        # 2. 🚦 Traffic Control
        
        if intent == "PRODUCT_SEARCH":
            query = decision.get("query") or message
            products, _ = await self.ai_engine.find_products_from_message(db, query, 0)
            response.text = await self._generate_product_response(products)
            response.explain = "Database Vector Search"

        elif intent == "TRACK_ORDER":
            order_id = decision.get("order_id")
            if order_id:
                response.text = f"On it! 🛰️ Locking onto telemetry for Order #{order_id}..."
                response.action = TrackOrderAction(action="track_order", payload={"order_id": order_id})
            else:
                response.text = "I'd love to track that for you! Do you have the Order ID handy? (It usually looks like numbers) 📦"
            response.explain = "Order Tracking Module"

        elif intent == "SUPPORT_HANDOFF":
            response.text = "I hear you, and I've got your back. Connecting you to a human specialist right now. 🎧 Stay with me."
            response.action = SupportHandoffAction(action="initiate_support_handoff", payload={})
            response.explain = "Priority Support Protocol"

        else: # SOCIAL_CHAT
            ai_reply = decision.get("social_reply", "I'm just happy to be chatting with you! 😊")
            response.text = ai_reply
            response.explain = "Generative Social Intelligence"

        # 3. 💾 Memory Update
        await self._save_context(session_id, context, message, response.text)
        
        return response

def get_neural_core_service(
    ai_engine: AICommerceEngine = Depends(get_ai_commerce_engine),
    cache: IAsyncCacheClient = Depends(get_cache_client)
) -> NeuralCoreService:
    return NeuralCoreService(ai_engine, cache)
