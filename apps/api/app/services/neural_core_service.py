import logging
import re
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select
from app.core.config import settings
from app import models
from app.models.aimemory import AIMemory
from app.schemas.ai_actions import (
    NeuralCoreResponse, 
    AddToCartAction, 
    TrackOrderAction, 
    ProductSearchAction, 
    SupportHandoffAction,
    PresentOptionsAction,
    QuickReplyOption
)
import datetime
import random
from app.models.product import Product 
from sqlalchemy import cast, String, or_

logger = logging.getLogger(__name__)

class ToolService:
    def product_search(self, db: Session, query: str) -> List[Dict[str, Any]]:
        if not query:
            return []
        
        search_query = f"%{query}%"
        
        statement = select(Product).where(
            or_(
                Product.name.ilike(search_query),
                Product.description.ilike(search_query),
                cast(Product.tags, String).ilike(search_query)
            )
        ).limit(3)
        
        products = db.exec(statement).all()
        
        return [
            {
                "id": p.id,
                "title": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.inventory
            }
            for p in products
        ]

class NeuralCoreService:
    def __init__(self):
        self.guest_session_memory: Dict[str, Dict[str, Any]] = {}
        self.tools = ToolService()
        self.SIMPLE_RESPONSE_MAP = {
            "SOCIAL_CHECK_IN": [
                "I’m doing great, thanks for asking 😊 How about you?",
                "All systems running perfectly — and you? Feeling good today?"
            ],
            "SOCIAL_RESPONSE": [
                "Glad to hear that 😊 Anything exciting happening today?",
                "Awesome! That’s what I like to hear 😄"
            ],
            "SELF_AWARENESS_QUERY": [
                "I am a specialized AI assistant, designed by airdeliver to help you.",
                "I exist within airdeliver's secure infrastructure to assist with your needs."
            ]
        }

    def _get_memory(self, db: Session, user: Optional[models.User], session_id: str) -> Dict[str, Any]:
        if user and user.id:
            memory_record = db.exec(select(AIMemory).where(AIMemory.user_id == user.id)).first()
            if not memory_record:
                memory_record = AIMemory(user_id=user.id, context_data={})
                db.add(memory_record)
                db.commit()
                db.refresh(memory_record)
            
            if not memory_record.context_data:
                 memory_record.context_data = {"turnIndex": 0, "user_name": user.full_name or "friend", "lastIntent": "GREETING"}
                 db.add(memory_record); db.commit()
                 
            return memory_record.context_data
        else:
            if session_id not in self.guest_session_memory:
                self.guest_session_memory[session_id] = {"turnIndex": 0, "user_name": "friend", "lastIntent": "GREETING"}
            return self.guest_session_memory[session_id]

    def _save_memory(self, db: Session, user: Optional[models.User], session_id: str, session_data: Dict[str, Any]):
        if user and user.id:
            memory_record = db.exec(select(AIMemory).where(AIMemory.user_id == user.id)).first()
            if memory_record:
                memory_record.context_data = session_data
                db.add(memory_record)
                db.commit()
        else:
            self.guest_session_memory[session_id] = session_data

    def _get_temporal_greeting(self, user_name: str) -> str:
        current_hour = datetime.datetime.now().hour
        if 5 <= current_hour < 12: return f"Good morning, {user_name} ☀️ How can I assist you?"
        if 12 <= current_hour < 18: return f"Hey {user_name} 😊 How can I help?"
        return f"Good evening, {user_name} 🌙 What can I do for you?"

    def _detect_emotion(self, user_message: str) -> str:
        message_lower = user_message.lower()
        if any(w in message_lower for w in ["awesome", "great", "love it", "excited"]): return "excited"
        if any(w in message_lower for w in ["help", "issue", "problem", "angry", "frustrated"]): return "frustrated"
        return "neutral"

    def _parse_intent(self, user_message: str, last_intent: str) -> Dict:
        message_lower = user_message.lower()
        cleaned_message = re.sub(r'[^\w\s]', '', message_lower).strip()

        if user_message == "__INITIAL_GREETING__":
            return {"intent": "GREETING"}

        greeting_keywords = ["hello", "hi", "hey", "مرحبا", "أهلا"]
        if any(kw in message_lower for kw in greeting_keywords):
            return {"intent": "GREETING"}

        check_in_pattern = r"^(how are you|how's it going|what's up|ازيك|عامل ايه|ايه الاخبار)"
        if re.search(check_in_pattern, message_lower):
            return {"intent": "SOCIAL_CHECK_IN"}

        awareness_patterns = [
           r"are you (real|a bot|human|a person|conscious|sentient|alive)",
           r"do you (sleep|eat|dream|feel|have feelings|have a body)",
           r"who are you", r"انت مين", r"اسمك ايه"
        ]
        if any(re.search(pattern, message_lower) for pattern in awareness_patterns):
           return {"intent": "SELF_AWARENESS_QUERY"}

        social_responses = {
            "i'm good", "im good", "fine", "doing well", "great", "not bad", 
            "i'm fine", "feeling good", "i feel good"
        }
        if any(keyword in cleaned_message for keyword in social_responses):
            return {"intent": "SOCIAL_RESPONSE"}

        social_responses_negative = {
            "not good", "bad", "sad", "terrible", "awful", "not great",
            "feeling bad", "i'm sad", "i feel bad", "تعبان", "متضايق", "زهقان"
        }
        if any(keyword in cleaned_message for keyword in social_responses_negative):
            return {"intent": "SOCIAL_RESPONSE_NEGATIVE"}
        
        inquiry_keywords = [
            "price", "cost", "available", "availability", "in stock", "do you have", 
            "do you sell", "how much", "what’s the price of", "is there", "how much is",
            "can i get", "any", "sell me", "find me",
            "سعر", "متاح", "موجود", "عندك", "في المخزون", "بكم"
        ]
        if any(kw in user_message for kw in inquiry_keywords):
            product_name = ""
            after_match_en = re.search(r'(?:price of|cost of|availability of|do you have|do you sell|what’s the price of|how much is|can i get|find me|sell me)\s+(.*)', message_lower)
            if after_match_en:
                product_name = after_match_en.group(1)
            
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

        support_keywords = ["support", "help", "agent", "someone real", "issue", "refund", "human"]
        if any(kw in message_lower for kw in support_keywords): return {"intent": "SUPPORT_HANDOFF"}

        track_match = re.search(r'(track|where is|eta for) my order\s*#?(\d+)', message_lower)
        if track_match: return {"intent": "TRACK_ORDER", "entities": {"order_id": track_match.group(2)}}
        
        track_match_generic = re.search(r'(track|where is|eta for) my order', message_lower)
        if track_match_generic: return {"intent": "TRACK_ORDER", "entities": {"order_id": None}}


        return {"intent": "UNKNOWN"}
    
    def handle_message(self, db: Session, message: str, user: Optional[models.User], session_id: str) -> NeuralCoreResponse:
        session_data = self._get_memory(db, user, session_id)
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
            text_response = "Hey There 👋, air intelligence activated. Ready to track orders, connect you directly to our team or check prices."
            action_payload = PresentOptionsAction(
                action="present_options",
                payload={
                    "options": [
                        QuickReplyOption(title="Track my recent order", payload="Track my order"),
                        QuickReplyOption(title="Talk to a human agent", payload="Transfer me to a human")
                    ]
                }
            )
            explain_text = "User initiated contact. Responded with hybrid interface (Text + Quick Replies)."

        elif intent in self.SIMPLE_RESPONSE_MAP:
            text_response = random.choice(self.SIMPLE_RESPONSE_MAP[intent])
        
        elif intent == "SOCIAL_RESPONSE_NEGATIVE":
            text_response = random.choice([
                "I'm sorry to hear that. Is there anything I can help with?",
                "That doesn't sound good. I'm here to help if you need to find anything.",
            ])
            explain_text = "User expressed a negative sentiment; responded with empathy."
        
        if text_response and not action_payload:
            session_data["lastIntent"] = intent
            self._save_memory(db, user, session_id, session_data)
            return NeuralCoreResponse(
                text=text_response, action=action_payload, explain=explain_text,
                confidence=confidence_score, telemetry={"intent": intent, "entities": entities_list}
            )
        
        if text_response and action_payload:
             session_data["lastIntent"] = intent
             self._save_memory(db, user, session_id, session_data)
             return NeuralCoreResponse(
                 text=text_response, action=action_payload, explain=explain_text,
                 confidence=confidence_score, telemetry={"intent": intent, "entities": entities_list}
             )

        try:
            if intent == "PRODUCT_INQUIRY":
                product_name = plan.get("entities", {}).get("product_name")
                if not product_name:
                    text_response = "Sure! Which product would you like me to check for you?"
                    explain_text = "User asked about price/availability without specifying a product."
                    intent = "PRODUCT_INQUIRY_CLARIFY"
                else:
                    explain_text = f"User asked about '{product_name}'. Calling internal ProductService."
                    search_results = self.tools.product_search(db, product_name)
                    
                    if not search_results:
                        text_response = f"Sorry 😔 I couldn’t find '{product_name.title()}' in our catalog right now."
                        intent = "PRODUCT_INQUIRY_FAILED"
                    else:
                        product = search_results[0]
                        availability = "in stock" if product.get("stock", 0) > 0 else "out of stock"
                        price = product.get("price")
                        title = product.get("title")
                        text_response = random.choice([
                            f"The **{title}** is {availability} and priced at ${price}.",
                            f"You got it! The **{title}** is currently {availability} and goes for ${price}.",
                        ])
                        intent = "present_product"
            
            elif intent == "SUPPORT_HANDOFF":
                text_response = "Of course 👍 I’ll connect you with a specialist right away."
                action_payload = SupportHandoffAction(action="initiate_support_handoff", payload={})
                explain_text = "User requested human support; initiating handover protocol."

            elif intent == "TRACK_ORDER":
                order_id = plan.get("entities", {}).get("order_id")
                if not order_id:
                    text_response = "Sure, I can help with that. Could you please confirm your latest order ID?"
                    explain_text = "User asked to track order without ID. Asking for clarification."
                else:
                    text_response = f"Checking on order #{order_id} now... (WIP: Order tracking logic)"
                    action_payload = TrackOrderAction(action="track_order", payload={"order_id": order_id})
                    explain_text = f"User requested tracking for order {order_id}. Initiating track."


        except Exception as e:
            logger.error(f"[NeuralCoreService] Tool execution failed: {e}")
            text_response = "I seem to have run into a system glitch. Please try again in a moment."
            explain_text = f"Exception during tool execution: {e}"
            intent = "SYSTEM_ERROR"

        if not text_response and not action_payload:
            text_response = "I'm not quite sure what you mean by that. Could you rephrase?"
            explain_text = "User intent was unclear or unsupported."
            confidence_score = 0.30
            intent = "UNKNOWN"

        session_data["lastIntent"] = intent
        self._save_memory(db, user, session_id, session_data)
        return NeuralCoreResponse(text=text_response, action=action_payload, explain=explain_text, confidence=confidence_score, telemetry={"intent": intent, "entities": entities_list})

neural_core_service = NeuralCoreService()
