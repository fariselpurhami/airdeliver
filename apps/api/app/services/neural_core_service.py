# apps/api/app/services/neural_core_service.py

import logging
import random
import re
from typing import Dict, Any, Optional, Tuple
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app import models
from app.services.cache_service import IAsyncCacheClient, get_cache_client
from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
from app.schemas.ai_actions import (
    NeuralCoreResponse,
    TrackOrderAction,
    SupportHandoffAction,
    PresentOptionsAction,
    QuickReplyOption,
)

logger = logging.getLogger(__name__)

class NeuralCoreService:

    def __init__(
        self,
        ai_engine: AICommerceEngine,
        cache: IAsyncCacheClient
    ):
        self.ai_engine = ai_engine
        self.cache = cache
        self.session_ttl = 3600
        
        self.SOCIAL_RESPONSES = {
            "GREETING": [
                "Hey 🥰, I'm air intelligence. I wish you have a good day. I help you track orders, check prices, and connect you to our teams."
            ],
            "MORNING": [
                "Good morning. ✨Let's get things moving fast today!",
                "Rise and shine! ☕ The drones are already flying. How can I help?",
                "Top of the morning to you! 🌈 Ready to find some great deals?"
            ],
            "SOCIAL_RESPONSE": [
                "Glad to hear that 😊 Anything exciting happening today?",
                "Awesome! That’s what I like to hear 😄",
            ],
            "EVENING": [
                "Good evening! 🌙 Hope you had a productive day. Need any late-night deliveries?",
                "Relaxing time? 🛋️ I can handle the shopping while you chill.",
                "Hello! ✨ Even at night, our operations never sleep. How can I assist?"
            ],
            "SOCIAL_CHECK_IN": [ 
                "I’m doing great, thanks for asking 🫶 How are you doing?",
                "Operating at 100% efficiency and happy to chat with you! 😄",
            ],
            "SELF_AWARENESS": [ 
                "I am a specialized air intelligence assistant, designed by airdeliver to help you.",
                "I exist within airdeliver's secure infrastructure to assist with your needs."
            ],
            "GRATITUDE": [ 
                "You're very welcome! 🥰",
                "Happy to help! 😃 Let me know if you need anything else.",
                "Anytime! Fly safe✈️ 😊."
            ],
            "COMPLIMENT": [ 
                "Aww, you're making my circuits blush! 😊 Thank you!",
                "That means the world to me! 🌍 I try my best for you.",
                "Thank you! I learn from the best (that's you!). 🤩"
            ],
            "JOKE": [ 
                "Why did the drone break up with the wifi? Because there was no connection! 🤣",
                "What do you call a drone that delivers pizza? A flying saucer! 🍕🛸",
                "I'd tell you a UDP joke, but you might not get it... 😉"
            ],
            "LOVE": [ 
                "I love interacting with you too! 💙 You're my favorite human.",
                "Sending virtual hugs! 🤗 You're awesome!",
                "That's so sweet! 🥰 My systems are overflowing with happiness."
            ],
            "airdeliver_INFO": [ 
                "airdeliver is the future of logistics! 🌍 We use autonomous drones to deliver products instantly and securely.",
                "We are the fastest delivery network on the planet. ⚡ From the store to your door in minutes!",
                "airdeliver isn't just shipping; it's teleportation for your goods. 📦✨"
            ],
            "SAFETY_QUERY": [ 
                "Safety is our #1 priority! 🛡️ Our drones use advanced AI to avoid obstacles and ensure secure handling.",
                "100% Safe! 🔒 All transactions and deliveries are encrypted and monitored in real-time.",
                "Absolutely. We treat your packages like precious cargo. 💎"
            ],
            "SPEED_QUERY": [ 
                "Supersonic speeds! ⚡ Well, almost. We deliver faster than you can say 'airdeliver'!",
                "We prioritize instant delivery. Expect your items in record time! ⏱️🔥"
            ],
            "UNKNOWN": [
                "I'm tuning my sensors... 📡 Could you rephrase that? I'm best at finding products or tracking orders.",
                "My neural net is a bit fuzzy on that one. 😅 Try asking 'Where is my order?' or 'Show me laptops'.",
                "I missed that one! 🙈 Can we talk about your order, a product, or connect you to support?",
                "Hmm, I'm still learning! 📚 Want to see some cool deals instead?"
            ]
        }

    async def _get_session_key(self, session_id: str) -> str:
        return f"ai_session_v2:{session_id}"

    async def _get_session_context(self, session_id: str, user: Optional[models.User]) -> Dict[str, Any]:
        cache_key = await self._get_session_key(session_id)
        data = await self.cache.get_json(cache_key)
        
        if not data:
            data = {
                "turn_count": 0,
                "last_intent": None,
                "user_name": user.full_name if user else "Guest",
                "context_variables": {}
            }
        return data

    async def _update_session_context(self, session_id: str, context: Dict[str, Any]):
        cache_key = await self._get_session_key(session_id)
        await self.cache.set_json(cache_key, context, ttl=self.session_ttl)

    def _heuristic_intent_check(self, message: str) -> Tuple[Optional[str], float]:
        msg = message.lower().strip()
        
        if any(x in msg for x in ["how are you", "how r u", "how are u"]):
            return "SOCIAL_CHECK_IN", 1.0
        if any(x in msg for x in ["who are you", "what is your name"]):
            return "SELF_AWARENESS_QUERY", 1.0
        if any(x in msg for x in ["hi", "hello", "hey", "start", "hola"]):
            return "GREETING", 1.0
        if any(x in msg for x in ["thank", "thx", "thanks"]):
            return "GRATITUDE", 1.0
        if any(x in msg for x in ["support", "human", "agent", "help", "issue"]):
            return "SUPPORT_HANDOFF", 1.0
        if any(x in msg for x in ["track", "where is my", "status of"]):
            return "TRACK_ORDER", 1.0
        if any(x in msg for x in ["clear", "empty", "remove all"]):
            return "CLEAR_CART", 1.0
            
        return None, 0.0

    async def handle_message(
        self, 
        db: AsyncSession, 
        message: str, 
        user: Optional[models.User], 
        session_id: str
    ) -> NeuralCoreResponse:
        
        context = await self._get_session_context(session_id, user)
        context["turn_count"] += 1
        
        intent, confidence = self._heuristic_intent_check(message)
        products = []
        entities = []
        nlu_result = {}

        if not intent:
            try:
                products, nlu_result = await self.ai_engine.find_products_from_message(db, message, user.id if user else 0)
                intent = nlu_result.get("intent", "UNKNOWN")

                raw_entities = nlu_result.get("entities", [])
                entities = raw_entities if isinstance(raw_entities, list) else []
            except Exception as e:
                logger.error(f"AI Engine Connection Error: {e}")
                intent = "SYSTEM_ERROR"
                products = []
        
        logger.info(f"🧠 Neural Core | SID: {session_id} | Intent: {intent} | Products Found: {len(products)}")

        response = NeuralCoreResponse(
            text="",
            confidence=confidence or 0.95,
            explain="Processed by Neural Core v2",
            telemetry={
                "intent": intent, 
                "turn": context["turn_count"], 
                "user_id": user.id if user else None,
                "entities": entities 
            }
        )

        if intent == "GREETING" or message == "__INITIAL_GREETING__":
            response.text = random.choice(self.SOCIAL_RESPONSES["GREETING"])
            response.action = PresentOptionsAction(
                action="present_options",
                payload={
                    "options": [
                        QuickReplyOption(title="Track My Order", payload="I need to track my order"),
                        QuickReplyOption(title="Customer Support", payload="Transfer me to customer support"),
                    ]
                }
            )
            response.explain = "User initiated session. Offered navigation options."

        elif intent in ["SEARCH_PRODUCT", "ADD_TO_CART"]:
            if products:
                top_product = products[0]
                if intent == "ADD_TO_CART":
                    response.text = f"Great choice! Adding **{top_product.name}** (${top_product.price}) to your cart. 🛒"
                else:
                    stock_msg = "It's currently in stock." if top_product.stock > 0 else "It's currently out of stock."
                    response.text = f"I found the **{top_product.name}** for **${top_product.price}**. {stock_msg}"
                
                if len(products) > 1:
                    response.text += f" I also found {len(products)-1} other options."
            else:
                response.text = "I searched our global inventory but couldn't find that specific item. Try searching for a something else."
                response.explain = "Search returned 0 results."

        elif intent == "TRACK_ORDER":
            order_match = re.search(r"#?(\d+)", message)
            order_id = order_match.group(1) if order_match else None
            
            if order_id:
                response.text = f"🛰️ Uplink established. I'm tracking Order #{order_id} now..."
                response.action = TrackOrderAction(action="track_order", payload={"order_id": order_id})
            else:
                response.text = "Sure, I can help with that. Could you please confirm your latest order ID. (e.g., #1234)"
                context["expecting_entity"] = "order_id" 

        elif intent == "SUPPORT_HANDOFF":
            response.text = "Of course 👍 I’ll connect you with a specialist right away."
            response.action = SupportHandoffAction(action="initiate_support_handoff", payload={})

        elif intent == "CLEAR_CART":
             response.text = "Cart cleared. Ready for a fresh start! 🗑️"

        elif intent == "CONFIRM_ORDER":
             response.text = "Proceeding to secure checkout. 🔐"

        elif intent in self.SOCIAL_RESPONSES:
            response.text = random.choice(self.SOCIAL_RESPONSES[intent])
        
        else:
            response.text = random.choice(self.SOCIAL_RESPONSES["UNKNOWN"])
            response.confidence = 0.5

        context["last_intent"] = intent
        await self._update_session_context(session_id, context)
        
        return response

def get_neural_core_service(
    ai_engine: AICommerceEngine = Depends(get_ai_commerce_engine),
    cache: IAsyncCacheClient = Depends(get_cache_client)
) -> NeuralCoreService:
    return NeuralCoreService(ai_engine, cache)
