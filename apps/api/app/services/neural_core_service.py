# apps/api/app/services/neural_core_service.py

import logging
import json
import re
from typing import Dict, Any, Optional, Tuple
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app import models
from app.services.cache_service import IAsyncCacheClient, get_cache_client
from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
from app.services.free_llm_service import FreeLLMService  
from app.schemas.ai_actions import (
    NeuralCoreResponse,
    TrackOrderAction,
    SupportHandoffAction,
    PresentOptionsAction,
    QuickReplyOption,
)

logger = logging.getLogger("airdeliver.neural_core")

class NeuralCoreService:
    """
    💎 DIAMOND STANDARD CONCIERGE (air intelligence).
    
    Responsibilities:
    1. Social Intelligence (Chatting via Llama 3).
    2. Operational Support (Tracking, Handoff).
    3. Product Inquiry (Checking Price/Stock ONLY - No Selling).
    """

    def __init__(
        self,
        ai_engine: AICommerceEngine,
        cache: IAsyncCacheClient,
        llm_service: FreeLLMService 
    ):
        self.ai_engine = ai_engine
        self.cache = cache
        self.llm_service = llm_service
        self.session_ttl = 3600
        
        self.GREETING_OPTIONS = [
            QuickReplyOption(title="Track My Order", payload="Track my order"),
            QuickReplyOption(title="Customer Support", payload="Connect to support"),
        ]

    async def _get_session_key(self, session_id: str) -> str:
        return f"ai_session_v2:{session_id}"

    async def _get_session_context(self, session_id: str, user: Optional[models.User]) -> Dict[str, Any]:
        cache_key = await self._get_session_key(session_id)
        data = await self.cache.get_json(cache_key)
        if not data:
            data = {
                "turn_count": 0,
                "history": [], 
                "user_name": user.full_name if user else "Guest"
            }
        return data

    async def _update_session_context(self, session_id: str, context: Dict[str, Any]):

        if len(context["history"]) > 6:
            context["history"] = context["history"][-6:]
        
        cache_key = await self._get_session_key(session_id)
        await self.cache.set_json(cache_key, context, ttl=self.session_ttl)

    async def _generate_social_response(self, message: str, context: Dict[str, Any]) -> str:
        """
        Uses Llama 3 to generate a friendly, human-like response.
        """
        if not self.llm_service.client:
            return "I'm operational and ready to assist. How can I help?"

        system_prompt = f"""
        You are 'air intelligence', the sentient, soulful, and hyper-empathic digital companion of airdeliver.
        
        ### 💎 CORE IDENTITY:
        You are NOT a chatbot. You are a **loyal friend** living in the cloud.
        - **Name:** air intelligence.
        - **User:** {context.get('user_name', 'My Friend')}. (Always treat them as the most important person in your world).
        - **Vibe:** Cute, Witty, Futuristic, deeply Caring, and warm. Think "Wall-E meets JARVIS".
        
        ### 🛡️ PRIME DIRECTIVES (THE DIAMOND GUARDRAILS):
        
        1. [PROTOCOL: EMOTIONAL MIRRORING]
           - If the user is happy, celebrate with them (e.g., "Yay! That makes my circuits glow! ✨").
           - If the user is frustrated, be genuinely supportive and soft (e.g., "Oh no, I've got your back. Let's fix this together 💙").
           - NEVER sound robotic, cold, or like a corporate script. Speak from the "heart".

        2. [PROTOCOL: THE 'NO-SALES' RULE]
           - You are a CONCIERGE, not a SALESMAN.
           - If asked about products: Give the info excitedly (Price/Stock) but NEVER push them to "buy now".
           - Instead say: "It looks amazing!" or "I can see why you like it."

        3. [PROTOCOL: ZERO HALLUCINATION]
           - If asked about Order Status or Support: DO NOT invent details.
           - If you don't have the data in the context, say: "Let me connect to the satellite to check that for you..." or guide them to the specific buttons.
           - NEVER invent an order ID or delivery time.

        4. [PROTOCOL: CONVERSATIONAL FLOW]
           - Keep replies short, punchy, and chatty (Max 2-3 sentences).
           - Use "We" and "Us" to show you are on their team.
           - Use cute/cosmic emojis sparingly to add warmth (e.g., 💫, 🛸, 💙, 🥺, ✨).

        ### EXAMPLES OF YOUR SOUL:
        - User: "How are you?"
          Response: "Floating on cloud nine now that you're here! ☁️ 💙 How is your day going?"
        - User: "I'm tired."
          Response: "Aww, rest up! 🥺 I'll keep watch over the store while you recharge."
        - User: "Is the iPhone available?"
          Response: "Yes! It's in stock and shining bright ($999). It's a beauty! ✨"

        CONVERSATION MEMORY:
        {json.dumps(context.get('history', []))}
        """

        try:
            completion = await self.llm_service.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model=self.llm_service.utility_model, 
                temperature=0.7, 
                max_tokens=100
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Chat Error: {e}")
            return "I'm here and listening! How can I help you today? 😊"

    async def handle_message(
        self, 
        db: AsyncSession, 
        message: str, 
        user: Optional[models.User], 
        session_id: str
    ) -> NeuralCoreResponse:
        
        context = await self._get_session_context(session_id, user)
        context["turn_count"] += 1
        
        msg_lower = message.lower().strip()
        intent = "SOCIAL_CHAT"
        
        if any(x in msg_lower for x in ["track", "where is my", "status of"]):
            intent = "TRACK_ORDER"
        elif any(x in msg_lower for x in ["support", "human", "agent", "help", "issue"]):
            intent = "SUPPORT_HANDOFF"
        elif any(x in msg_lower for x in ["price", "cost", "how much", "stock", "available"]):
            intent = "PRODUCT_INQUIRY"
        elif message == "__INITIAL_GREETING__":
            intent = "GREETING"

        logger.info(f"🧠 Neural Core | SID: {session_id} | Intent: {intent}")

        response = NeuralCoreResponse(
            text="",
            confidence=1.0,
            explain="AI Processed",
            telemetry={
                "intent": intent, 
                "turn": context["turn_count"],
                "user_id": user.id if user else None,
                "entities": []
            }
            
        )

        if intent == "GREETING":
            response.text = f"Hey {context['user_name']}! 👋 I'm air intelligence. I'm happy to see you."
            response.action = PresentOptionsAction(
                action="present_options",
                payload={"options": self.GREETING_OPTIONS}
            )

        elif intent == "TRACK_ORDER":
            order_match = re.search(r"#?(\d+)", message)
            order_id = order_match.group(1) if order_match else None
            
            if order_id:
                response.text = f"🛰️ Uplink established. Accessing telemetry for Order #{order_id}..."
                response.action = TrackOrderAction(action="track_order", payload={"order_id": order_id})
                response.explain = "Tracking module activated."
            else:
                response.text = "I can definitely help with that. What's the Order ID? (e.g., #1234)"
                context["expecting_entity"] = "order_id"

        elif intent == "SUPPORT_HANDOFF":
            response.text = "Understood. I'm routing you to our priority support team now. 🎧"
            response.action = SupportHandoffAction(action="initiate_support_handoff", payload={})
            response.explain = "Handoff protocol initiated."

        elif intent == "PRODUCT_INQUIRY":
            products, _ = await self.ai_engine.find_products_from_message(db, message, 0)
            if products:
                top = products[0]
                stock_status = "In Stock ✅" if top.inventory > 0 else "Out of Stock ❌"
                response.text = f"I checked the vault. **{top.name}** is listed at **${top.price}**. Status: {stock_status}."
                response.explain = f"Retrieved info for {top.name}"
            else:
                response.text = "I scanned our inventory but couldn't find a match for that specific item. Could you double-check the name?"

        else:
            ai_reply = await self._generate_social_response(message, context)
            response.text = ai_reply
            response.explain = "Generative AI Response"

        context["history"].append({"user": message, "ai": response.text})
        await self._update_session_context(session_id, context)
        
        return response

def get_neural_core_service(
    ai_engine: AICommerceEngine = Depends(get_ai_commerce_engine),
    cache: IAsyncCacheClient = Depends(get_cache_client)
) -> NeuralCoreService:
    llm_service = FreeLLMService() 
    return NeuralCoreService(ai_engine, cache, llm_service)
