# file: apps/api/app/services/neural_core_service.py
import logging
import httpx
import re
from typing import Dict, Any, List
from sqlmodel import Session, select
from app.core.config import settings
from app import models
from app.models.user import AIMemory  # Import the new persistent memory model
from app.schemas.ai_actions import NeuralCoreResponse, AddToCartAction, TrackOrderAction, ProductSearchAction, SupportHandoffAction
import datetime
import random

logger = logging.getLogger(__name__)

class NeuralCoreService:
    def __init__(self):
        self.api_base_url = f"http://127.0.0.1:8000{settings.API_V1_STR}/tools"
        self.session_memory: Dict[str, Any] = {}

    SIMPLE_RESPONSE_MAP = {
        "SOCIAL_CHECK_IN": [
            "I’m doing great, thanks for asking 😊 How about you?",
            "Everything’s smooth on my side 😄 How are you doing?",
            "All systems running perfectly — and you? Feeling good today?"
        ],
        "SOCIAL_RESPONSE": [
            "Glad to hear that 😊 Anything exciting happening today?",
            "Awesome! That’s what I like to hear 😄",
            "Nice! I like your energy ⚡ Want me to show you what’s trending today?"
        ],
        "SELF_AWARENESS_QUERY": [
            "As real as a digital mind can be. I exist inside airdeliver’s systems.",
            "Sleep? I analyze dreams in data form 😴 But tell me, how’s your day been?"
        ]
    }

    def _get_or_create_memory(self, db: Session, user: models.User) -> AIMemory:
        """Retrieves or creates a persistent memory record for the user from the database."""
        memory = db.exec(select(AIMemory).where(AIMemory.user_id == user.id)).first()
        if not memory:
            memory = AIMemory(user_id=user.id, context_data={
                "turnIndex": 0,
                "user_name": user.full_name or "friend",
                "lastIntent": "GREETING"
            })
            db.add(memory)
            db.commit()
            db.refresh(memory)
        return memory

    def _get_temporal_greeting(self, user_name: str) -> str:
        current_hour = datetime.datetime.now().hour
        if 5 <= current_hour < 12: return f"Good morning, {user_name} ☀️ Let’s make today count."
        if 12 <= current_hour < 18: return f"Hey {user_name} 😊 Hope your day’s going smoothly."
        return f"Good evening, {user_name} 🌙 Ready to explore something new?"

    def _detect_emotion(self, user_message: str) -> str:
        message_lower = user_message.lower()
        if any(w in message_lower for w in ["awesome", "great", "love it", "excited"]): return "excited"
        if any(w in message_lower for w in ["tired", "exhausted", "long day"]): return "tired"
        if any(w in message_lower for w in ["help", "issue", "problem", "angry", "frustrated"]): return "frustrated"
        return "neutral"

    def _parse_intent(self, user_message: str, last_intent: str) -> Dict:
        """--- NLU with Conversational Understanding Layer (Upgraded) ---"""
        message_lower = user_message.lower()

        # 1. Contextual Confirmation Logic
        positive_confirmations = ["yes", "sure", "ok", "yep", "do it", "add it", "add to cart"]
        if last_intent == "present_product" and any(kw in message_lower for kw in positive_confirmations):
            return {"intent": "CONFIRM_ADD_TO_CART"}

        # 2. Social & Emotional Intents
        greeting_keywords = ["hello", "hi", "hey", "مرحبا", "أهلا"]
        if any(kw in message_lower for kw in greeting_keywords):
            return {"intent": "GREETING"}

        check_in_pattern = r"^(how are you|how's it going|how have you been|how are things|what's up|what's new|what's going on|sup|ازيك|عامل ايه|ايه الاخبار)"

        if re.search(check_in_pattern, message_lower):
            return {"intent": "SOCIAL_CHECK_IN"}

        awareness_patterns = [
           r"are you (real|a bot|human|a person|conscious|sentient|alive)",
           r"do you (sleep|eat|dream|feel|have feelings|have a body)",
           r"can you (feel|dream|think)",
           r"what is your name",
           r"who are you",
           # Arabic variations
           r"هل انت (حقيقي|بوت|انسان|واعي|شخص)",
           r"انت مين",
           r"اسمك ايه",
           r"بتنام|بتاكل|بتحلم|بتحس|عندك مشاعر"
        ]

        if any(re.search(pattern, message_lower) for pattern in awareness_patterns):
           return {"intent": "SELF_AWARENESS_QUERY"}

        social_responses = {
            "i'm good", "im good", "fine", "doing well", "great", "not bad", 
            "i'm fine", "feeling good", "i feel good", "yeah good", 
            "pretty good", "so good", "feeling so good", "all good",
            "thanks", "thank you" # Added thanks as a social response
        }

        cleaned_message = re.sub(r'[^\w\s]', '', message_lower).strip()

        # --- FIX 1: Check if ANY keyword is IN the message (Partial Match) ---
        if any(keyword in cleaned_message for keyword in social_responses):
            return {"intent": "SOCIAL_RESPONSE"}

        # --- FIX 2: Understand Negative Social Responses ---
        social_responses_negative = {
            "not good", "bad", "sad", "terrible", "awful", "not great",
            "feeling bad", "i'm sad", "i feel bad", "تعبان", "متضايق", "زهقان"
        }
        if any(keyword in cleaned_message for keyword in social_responses_negative):
            return {"intent": "SOCIAL_RESPONSE_NEGATIVE"}

        # 3. Operational & Functional Intents
        
        inquiry_keywords = [
            "price", "cost", "available", "availability", "in stock", "do you have", 
            "do you sell", "how much", "what’s the price of", "is there", "how much is",
            "do you got", "can i get", "any", "sell me", "find me",
            "سعر", "متاح", "موجود", "عندك", "في المخزون", "بكم"
        ]
        if any(kw in user_message for kw in inquiry_keywords):
            product_name = ""
            after_match_en = re.search(r'(?:price of|cost of|availability of|do you have|do you sell|what’s the price of|how much is|can i get|find me|sell me)\s+(.*)', message_lower)
            if after_match_en:
                product_name = after_match_en.group(1)
            else:
                before_match_en = re.search(r'(?:is|are)\s+(?:the\s+)?(.*?)\s+(?:in stock|available|any)\??', message_lower)
                if before_match_en:
                    product_name = before_match_en.group(1)
            
            if not product_name:
                after_match_ar = re.search(r'(?:هل\s+)?(سعر|عندك|بكم)\s+(.*)', user_message)
                if after_match_ar:
                    product_name = after_match_ar.group(2)
                else:
                    before_match_ar = re.search(r'(.*)\s+(متاح|موجود|في المخزون)\??', user_message)
                    if before_match_ar:
                        product_name = before_match_ar.group(1)

            if product_name:
                product_name = product_name.strip().rstrip('?').strip().lower()

            return {"intent": "PRODUCT_INQUIRY", "entities": {"product_name": product_name or None}}

        support_keywords = ["support", "help", "agent", "someone real", "issue", "refund"]
        if any(kw in message_lower for kw in support_keywords): return {"intent": "SUPPORT_HANDOFF"}

        track_match = re.search(r'(track|where is|eta for) my order\s*#?(\d+)', message_lower)
        if track_match: return {"intent": "TRACK_ORDER", "entities": {"order_id": track_match.group(2)}}

        buy_keywords = ['buy', 'get', 'want', 'order', 'search for']
        for keyword in buy_keywords:
            if keyword in message_lower:
                query = message_lower.split(keyword, 1)[1].strip()
                if query: return {"intent": "BUY_PRODUCT", "entities": {"product_name": query}}

        return {"intent": "UNKNOWN"}
    
    def handle_message(self, db: Session, message: str, user: models.User) -> NeuralCoreResponse:
        memory_record = self._get_or_create_memory(db, user)
        session_data = memory_record.context_data
        session_data["turnIndex"] = session_data.get("turnIndex", 0) + 1

        last_intent = session_data.get("lastIntent")
        detected_emotion = self._detect_emotion(message)
        plan = self._parse_intent(message, last_intent)
        intent = plan.get("intent")

        text_response = ""
        action_payload = None
        explain_text = f"Detected emotion: {detected_emotion}. Responded to intent: {intent}."
        confidence_score = 0.98
        entities_dict = plan.get("entities", {})
        entities_list = [v for v in entities_dict.values() if v is not None]

        if intent == "GREETING": 
            text_response = self._get_temporal_greeting(session_data["user_name"])

        elif intent in self.SIMPLE_RESPONSE_MAP:
            text_response = random.choice(self.SIMPLE_RESPONSE_MAP[intent])
        
        # --- FIX 2: Handle Negative Responses Empathetically ---
        elif intent == "SOCIAL_RESPONSE_NEGATIVE":
            text_response = random.choice([
                "Oh no, I'm sorry to hear that. 😔 Is there anything I can help with?",
                "That doesn't sound good. I'm here to help if you need to find anything.",
                "I'm sorry things aren't great. Let me know if I can assist with anything."
            ])
            explain_text = "User expressed a negative sentiment; responded with empathy."
        
        if text_response:
            session_data["lastIntent"] = intent
            memory_record.context_data = session_data
            db.add(memory_record); db.commit()
            
            return NeuralCoreResponse(
                text=text_response,
                action=action_payload,
                explain=explain_text,
                confidence=confidence_score,
                telemetry={"intent": intent, "entities": entities_list}
            )

        try:
            with httpx.Client(timeout=10.0) as client:
                if intent == "PRODUCT_INQUIRY":
                    product_name = plan.get("entities", {}).get("product_name")
                    if not product_name:
                        text_response = "Sure  Which product would you like me to check for you?"
                        explain_text = "User asked about price/availability without specifying a product."
                        intent = "PRODUCT_INQUIRY_CLARIFY"
                    else:
                        explain_text = "User asked about product availability or price."
                        logger.info(f"Querying PRODUCT_SEARCH for: {product_name}")
                        api_response = client.get(f"{self.api_base_url}/PRODUCT_SEARCH", params={"query": product_name})
                        api_response.raise_for_status()
                        search_results = api_response.json()
                        logger.info(f"PRODUCT_SEARCH returned: {len(search_results)} results")

                        if not search_results and re.search(r'[\u0600-\u06FF]', product_name):
                            try:
                                from googletrans import Translator
                                translator = Translator()
                                translated_name = translator.translate(product_name, src='ar', dest='en').text
                                logger.info(f"Translated product name '{product_name}' -> '{translated_name}'")
                                api_response = client.get(f"{self.api_base_url}/PRODUCT_SEARCH", params={"query": translated_name})
                                api_response.raise_for_status()
                                search_results = api_response.json()
                                logger.info(f"PRODUCT_SEARCH (after translation) returned: {len(search_results)} results")
                            except Exception as e:
                                logger.error(f"Translation or fallback search failed: {e}")

                        if not search_results:
                            text_response = f"Sorry 😔 I couldn’t find '{product_name.title()}' in our catalog right now."
                            intent = "PRODUCT_INQUIRY_FAILED"
                        else:
                            product = search_results[0]
                            availability = "in stock ✅" if product.get("stock", 0) > 0 else "out of stock ❌"
                            price = product.get("price")
                            title = product.get("title")
                            text_response = random.choice([
                                f"The **{title}** is {availability} and priced at ${price}.",
                                f"You got it! The **{title}** is currently {availability} and goes for ${price}. Want to grab it? 🛒",
                                f"Currently, the **{title}** is priced at ${price} and it's {availability}."
                            ])
                            # --- FIX 3: Override intent to set context for next turn ---
                            intent = "present_product"
                
                elif intent == "SUPPORT_HANDOFF":
                    text_response = "Of course 👍 I’ll connect you with a specialist right away."
                    action_payload = SupportHandoffAction(action="initiate_support_handoff")
                    explain_text = "User requested human support; initiating handover protocol."

        except Exception as e:
            logger.error(f"[NeuralCoreService] Product inquiry failed: {e}")
            text_response = "I seem to have run into a system glitch. Please try again in a moment."
            explain_text = f"Exception during tool execution: {e}"
            intent = "SYSTEM_ERROR"

        if not text_response and not action_payload:
            text_response = random.choice([
                "I'm not quite sure what you mean by that. Could you rephrase?",
                "Hmm, I didn’t quite catch that — can you clarify?",
                "Could you tell me a bit more about what you mean?"
            ])
            explain_text = "User intent was unclear or unsupported."
            confidence_score = 0.30
            intent = "UNKNOWN"

        session_data["lastIntent"] = intent
        memory_record.context_data = session_data
        db.add(memory_record); db.commit()
        return NeuralCoreResponse(text=text_response, action=action_payload, explain=explain_text, confidence=confidence_score, telemetry={"intent": intent, "entities": entities_list})

neural_core_service = NeuralCoreService()
