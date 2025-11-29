# apps/api/app/services/ai_nlu_service.py

import logging
import random
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, and_
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import IAsyncCacheClient
from app.services.free_llm_service import FreeLLMService  
from app.models.product import Product

logger = logging.getLogger(__name__)

class AINLUService:
    """
    The Orchestrator of User Intent.
    Combines Vector Search (RAG) with Generative AI (Llama 3) for hyper-personalized commerce.
    Features Smart Recovery for complex queries.
    """
    def __init__(
        self,
        db: AsyncSession,
        search_engine: AICommerceEngine,
        rabbitmq: RabbitMQService,
        cache: IAsyncCacheClient,
        llm_service: FreeLLMService, 
    ):
        self.db = db
        self.search_engine = search_engine
        self.rabbitmq = rabbitmq
        self.cache = cache
        self.llm_service = llm_service
        self.seen_cache_ttl = 3600

        self.persona_anchors = {
            "LUXURY": self.search_engine.embedding_model.encode("expensive premium gold diamond luxury elegant exclusive high-end", convert_to_numpy=True),
            "TECH": self.search_engine.embedding_model.encode("technology computer electronics smart specs performance gadget innovation", convert_to_numpy=True),
            "FASHION": self.search_engine.embedding_model.encode("style clothes fashion trend wear outfit design aesthetic", convert_to_numpy=True),
            "CASUAL": self.search_engine.embedding_model.encode("simple basic home daily essentials standard cheap", convert_to_numpy=True)
        }

    # --- Helper Methods ---
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
        ids = [str(p['id'] if isinstance(p, dict) else p.id) for p in products]
        try:
            await self.cache.sadd(key, *ids)
            await self.cache.expire(key, self.seen_cache_ttl)
        except Exception: pass

    def _detect_persona(self, product: Product) -> str:
        """Detects product vibe using vector dot product against anchors."""
        product_text = f"{product.name} {product.description} {product.category} {' '.join(product.tags or [])}"
        product_vector = self.search_engine.embedding_model.encode(product_text, convert_to_numpy=True)
        best_persona = "CASUAL"
        max_score = -1.0
        for persona, anchor_vector in self.persona_anchors.items():
            score = np.dot(product_vector, anchor_vector) / (np.linalg.norm(product_vector) * np.linalg.norm(anchor_vector))
            if score > max_score:
                max_score = score
                best_persona = persona
        return best_persona

    def _get_contextual_message(self, persona: str, intent: str, product_name: str = "") -> str:
        """Fallback rule-based responses for high-speed interactions."""
        hour = datetime.now().hour
        time_context = "morning" if 5 <= hour < 12 else "evening" if 17 <= hour < 23 else "day"

        if intent == "ADD":
            if persona == "LUXURY": return f"An exquisite choice. **{product_name}** defines elegance. ✨"
            elif persona == "TECH": return f"**{product_name}** added. High-performance specs secured. ⚡"
            elif persona == "FASHION": return f"**{product_name}** is stunning! You have a great eye for style. 👗"
            else: return f"**{product_name}** is in! Great pick for your {time_context}. 🚀"
        if intent == "BUNDLE":
            if persona == "LUXURY": return "Curated specifically for your taste, a complete experience:"
            elif persona == "TECH": return "Optimized ecosystem bundle detected. Maximize your setup:"
            else: return "Grab the complete combo and save time:"
        if intent == "RECOVERY":
            if persona == "TECH": return "Specs didn't match? Check these alternatives:"
            else: return f"Change of heart on **{product_name}**? Maybe these fit better:"
        return f"**{product_name}** added!"

    async def _get_global_backup_products(self) -> List[Dict[str, Any]]:
        cache_key = "global:trending_products:v1"
        cached_products = await self.cache.get_json(cache_key)
        if cached_products: return cached_products
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
        return fresh_candidates

    async def _handle_initial_suggestions(self, user_id: int):
        backup_pool = await self._get_global_backup_products()
        hour = datetime.now().hour
        weighted_pool = []
        for p in backup_pool:
            cat = p.get('category', '').lower()
            if 6 <= hour < 11 and 'coffee' in cat: weighted_pool.extend([p]*3)
            elif 18 <= hour < 23 and 'game' in cat: weighted_pool.extend([p]*3)
            else: weighted_pool.append(p)

        final_selection = await self._filter_candidates(user_id, weighted_pool, limit=10)
        if not final_selection:
            await self.cache.delete(self._get_seen_key(user_id))
            final_selection = random.sample(backup_pool, min(len(backup_pool), 10)) if backup_pool else []

        if final_selection:
            await self._mark_products_as_seen(user_id, final_selection)
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": "Welcome! Based on your style, here are today's top picks:", "type": "proactive_suggestion", "products": final_selection, "reason": "AI Prediction"},
                "airdeliver.ai.response.out",
            )

    async def process_removal_recovery(self, payload: dict):
        user_id = payload["user_id"]
        removed_id = payload.get("removed_product_id")
        removed_name = payload.get("removed_product_name", "item")
        await self._mark_products_as_seen(user_id, [{"id": removed_id}])

        removed_product = await self.db.get(Product, removed_id)
        if not removed_product: return

        persona = self._detect_persona(removed_product)
        statement = select(Product).where(and_(Product.category == removed_product.category, Product.id != removed_id)).limit(10)
        alternatives = (await self.db.exec(statement)).all()
        alt_data = [p.model_dump(mode='json') for p in alternatives]
        final_selection = await self._filter_candidates(user_id, alt_data, limit=3)

        if final_selection:
            msg = self._get_contextual_message(persona, "RECOVERY", removed_name)
            await self._mark_products_as_seen(user_id, final_selection)
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": msg, "type": "proactive_suggestion", "products": final_selection, "reason": "Smart Recovery"},
                "airdeliver.ai.response.out",
            )

    async def _handle_secondary_suggestions(self, user_id: int, added_product: Product):
        final_products = []
        suggestion_reason = ""
        persona = self._detect_persona(added_product)

        if added_product.price > 100:
            bundle_items = await self.search_engine.generate_smart_bundle(self.db, added_product)
            if bundle_items:
                bundle_data = [p.model_dump(mode='json') for p in bundle_items]
                final_products = await self._filter_candidates(user_id, bundle_data, limit=3)
                if final_products:
                    suggestion_reason = self._get_contextual_message(persona, "BUNDLE")

        if not final_products:
            try:
                complementary = await self.search_engine.find_complementary_products(db=self.db, anchor_product=added_product, limit=20)
                comp_data = [p.model_dump(mode='json') for p in complementary]
                final_products = await self._filter_candidates(user_id, comp_data, limit=5)
                if final_products:
                    suggestion_reason = f"Perfect matches for your **{added_product.name}**:"
            except Exception: pass

        if not final_products:
            backup_pool = await self._get_global_backup_products()
            final_products = await self._filter_candidates(user_id, backup_pool, limit=5)
            suggestion_reason = "You might also like these popular items:"

        if final_products:
            await self._mark_products_as_seen(user_id, final_products)
            await self.rabbitmq.publish(
                {"user_id": user_id, "content": suggestion_reason, "type": "proactive_suggestion", "products": final_products, "reason": "Context-Aware"},
                "airdeliver.ai.response.out",
            )

    async def _handle_add_to_cart_success(self, user_id: int, product: Product):
        await self._mark_products_as_seen(user_id, [{"id": product.id}])
        persona = self._detect_persona(product)
        msg = self._get_contextual_message(persona, "ADD", product.name)
        await self.rabbitmq.publish({"user_id": user_id, "content": msg, "type": "success_text"}, "airdeliver.ai.response.out")
        await self._handle_secondary_suggestions(user_id, product)
        await self._send_confirmation_prompt(user_id)

    async def _send_confirmation_prompt(self, user_id: int):
        await self.rabbitmq.publish(
            {"user_id": user_id, "content": "I'm ready when you are. Proceed to checkout?", "type": "confirmation_prompt", "options": ["Confirm Order", "Clear Cart"]},
            "airdeliver.ai.response.out",
        )

    
    async def process_message(self, message_payload: dict):
        user_id = message_payload.get("user_id")
        raw_message = message_payload.get("message")
        message_text = str(raw_message).strip() if raw_message and not isinstance(raw_message, dict) else ""
        if not message_text: return

        if message_text.startswith("__INTERNAL_"):
            await self._process_internal_command(user_id, message_text)
            return

        products, entities = await self.search_engine.find_products_from_message(self.db, message_text, user_id)
        intent = entities.get("intent", "SEARCH_PRODUCT")

        if intent == "CONFIRM_ORDER":
            await self.rabbitmq.publish({**message_payload, "user_id": user_id}, "airdeliver.ai.intent.confirm_order")
            return
        if intent == "CLEAR_CART":
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": True}, "airdeliver.ai.intent.clear_cart")
            return

        if intent == "ADD_TO_CART":
            if not products:
                 
                 clean_query = await self.llm_service.extract_search_terms(message_text)
                 if clean_query != message_text:
                     products, _ = await self.search_engine.find_products_from_message(self.db, clean_query, user_id)

            if not products:
                 await self.rabbitmq.publish({"user_id": user_id, "content": f"I couldn't find exactly '{message_text}', but check these out:", "type": "product_carousel", "products": []}, "airdeliver.ai.response.out")
            elif len(products) > 1:
                 await self.rabbitmq.publish({"user_id": user_id, "content": f"Great choice ✨ I found a few different types of '{message_text}'. Which one catches?:", "type": "proactive_suggestion", "products": [p.model_dump(mode='json') for p in products[:10]]}, "airdeliver.ai.response.out")
            else:
                added_product = products[0]
                await self.rabbitmq.publish({"user_id": user_id, "product_id": added_product.id, "quantity": 1}, "airdeliver.ai.intent.add_to_cart")
                await self._handle_add_to_cart_success(user_id, added_product)

        elif intent == "SEARCH_PRODUCT":
            
            if not products:
                logger.info(f"🔎 First pass failed for: '{message_text}'. Attempting AI Extraction...")
                clean_query = await self.llm_service.extract_search_terms(message_text)
                
                if clean_query and clean_query.lower() != message_text.lower():
                    logger.info(f"🔄 Smart Retry: '{clean_query}'")
                    products, _ = await self.search_engine.find_products_from_message(self.db, clean_query, user_id)

            if not products:
                
                await self.rabbitmq.publish({"user_id": user_id, "content": f"I scanned the inventory for '{message_text}' but found no exact matches. Try browsing categories.", "type": "error"}, "airdeliver.ai.response.out")
                return

            candidate_pool = [p.model_dump(mode='json') for p in products[:15]]
            
            ai_reasoning = await self.llm_service.filter_and_recommend(
                user_query=message_text,
                products=candidate_pool
            )

            final_display_products = []
            intro_message = "Found these for you:"

            if ai_reasoning and ai_reasoning.selected_ids:
            
                intro_message = ai_reasoning.intro_message
                for p in candidate_pool:
                    if p['id'] in ai_reasoning.selected_ids:
            
                        p['ai_notes'] = ai_reasoning.reasoning.get(p['id'], "Best Match")
                        final_display_products.append(p)


                if not final_display_products:
                    logger.warning("⚠️ AI filtered out everything. Falling back to raw search.")
                    final_display_products = candidate_pool[:5]
                    intro_message = "Here are the best matches from our inventory:"

            else:
                logger.info("ℹ️ Using Standard RAG Fallback (AI returned empty selection).")
                final_display_products = candidate_pool[:5]
                intro_message = "Found these items matching your specifications:"
            
            await self._mark_products_as_seen(user_id, final_display_products)
            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": intro_message, 
                "type": "product_carousel", 
                "products": final_display_products,
                "reason": "AI Optimized"
            }, "airdeliver.ai.response.out")

    async def _process_internal_command(self, user_id: int, command: str):
        if command == "__INTERNAL_SAVE_FOR_LATER__":
            await self.rabbitmq.publish({"user_id": user_id, "content": "Saved to wishlist. 💾", "type": "success_text"}, "airdeliver.ai.response.out")
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
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": pid, "quantity": 1}, "airdeliver.ai.intent.add_to_cart")
                p = await self.db.get(Product, pid)
                if p: await self._handle_add_to_cart_success(user_id, p)
            except Exception: pass
            return
        if command.startswith("__INTERNAL_REMOVE_BY_ID__:") and user_id:
            try:
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": pid, "action": "remove_by_id"}, "airdeliver.ai.intent.remove_from_cart")
                await self.process_removal_recovery({"user_id": user_id, "removed_product_id": pid, "removed_product_name": "Item"})
            except Exception: pass
            return
