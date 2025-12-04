# apps/api/app/services/ai_nlu_service.py

import logging
import asyncio
import random
import re
from datetime import datetime
from typing import List, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, and_
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import IAsyncCacheClient
from app.services.free_llm_service import FreeLLMService
from app.models.product import Product

logger = logging.getLogger(__name__)

class AINLUService:
    """
    The Order With Air Brain (v24.0 - Golden Standard).
    Features:
    - Deep Research Display (Fixed for Original Frontend).
    - Thread-Safe Execution.
    - Full Sales Tactics (Bundles, Accessories, Recovery).
    - Context & Command Awareness.
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

    # --- 🧠 UTILITIES ---
    def _get_time_context(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12: return "morning"
        if 12 <= hour < 17: return "afternoon"
        if 17 <= hour < 22: return "evening"
        return "night"

    def _get_seen_key(self, user_id: int) -> str:
        return f"ai_session:{user_id}:seen_products"
    
    def _get_cart_key(self, user_id: int) -> str:
        return f"ai_cart:{user_id}"

    async def _mark_products_as_seen(self, user_id: int, products: List[Dict[str, Any]]):
        if not products: return
        async def _bg_task():
            key = self._get_seen_key(user_id)
            ids = [str(p['id'] if isinstance(p, dict) else p.id) for p in products]
            try:
                await self.cache.sadd(key, *ids)
                await self.cache.expire(key, self.seen_cache_ttl)
            except Exception: pass
        asyncio.create_task(_bg_task())

    # --- 🛡️ TEXT COMMAND GUARD ---
    async def _handle_text_commands(self, user_id: int, text: str) -> bool:
        clean_text = text.lower().strip()
        
        # Clear Cart
        if any(x in clean_text for x in ["clear cart", "empty cart", "delete all", "remove all"]):
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": True}, "airdeliver.ai.intent.clear_cart")
            return True
            
        # Checkout
        if any(x in clean_text for x in ["checkout", "pay now", "confirm order", "finish order"]):
            await self.rabbitmq.publish({"user_id": user_id, "content": {}, "type": "payment_intent"}, "airdeliver.ai.intent.confirm_order")
            return True

        # Reset/Help
        if clean_text in ["reset", "start over", "restart", "help"]:
            await self._process_internal_command(user_id, "__INTERNAL_RESET_SESSION__")
            await self._handle_initial_suggestions(user_id)
            return True

        return False

    # --- 🛒 SALES TACTICS ---

    async def _get_global_backup_products(self) -> List[Dict[str, Any]]:
        cache_key = "global:trending_products:v1"
        cached_products = await self.cache.get_json(cache_key)
        if cached_products: return cached_products
        statement = select(Product).order_by(Product.rating.desc()).limit(20)
        products = (await self.db.exec(statement)).all()
        if products:
            products_data = [p.model_dump(mode='json') for p in products]
            await self.cache.set_json(cache_key, products_data, ttl=600)
            return products_data
        return []

    async def _handle_secondary_suggestions(self, user_id: int, added_product: Product):
        final_products = []
        suggestion_reason = ""
        
        # Tier 1: Smart Bundle
        if added_product.price > 150:
            bundle_items = await self.search_engine.generate_smart_bundle(self.db, added_product)
            if bundle_items:
                final_products = [p.model_dump(mode='json') for p in bundle_items[:3]]
                suggestion_reason = f"🔥 Complete your setup! {added_product.name} works best with:"

        # Tier 2: Accessories
        if not final_products:
            comps = await self.search_engine.find_complementary_products(self.db, added_product, limit=5)
            if comps:
                final_products = [p.model_dump(mode='json') for p in comps[:4]]
                suggestion_reason = f"💡 Essential add-ons for your {added_product.name}:"

        # Tier 3: Category Match
        if not final_products:
            statement = select(Product).where(
                and_(Product.category == added_product.category, Product.id != added_product.id)
            ).order_by(Product.rating.desc()).limit(5)
            same_cat = (await self.db.exec(statement)).all()
            if same_cat:
                final_products = [p.model_dump(mode='json') for p in same_cat[:4]]
                suggestion_reason = f"Excellent choice! People also viewed these {added_product.category} items:"

        # Tier 4: Global Fallback
        if not final_products:
            global_picks = await self._get_global_backup_products()
            final_products = random.sample(global_picks, min(len(global_picks), 4)) if global_picks else []
            suggestion_reason = "Since you have great taste, check out what everyone else is buying:"

        if final_products:
            await asyncio.sleep(1.0)
            await self._mark_products_as_seen(user_id, final_products)
            await self.rabbitmq.publish({
                "user_id": user_id,
                "content": suggestion_reason,
                "type": "proactive_suggestion",
                "products": final_products,
                "reason": "Smart Suggestion"
            }, "airdeliver.ai.response.out")

    async def _handle_removal_recovery(self, user_id: int, product_id: int):
        removed_product = await self.db.get(Product, product_id)
        if not removed_product: return

        alternatives = await self.search_engine.perform_hybrid_search_pure(
            self.db, 
            f"alternative to {removed_product.name} {removed_product.category}", 
            limit=5
        )
        alternatives = [p for p in alternatives if p.id != product_id][:3]

        if alternatives:
            alt_data = [p.model_dump(mode='json') for p in alternatives]
            await self.rabbitmq.publish({
                "user_id": user_id,
                "content": f"Changed your mind about **{removed_product.name}**? Maybe one of these fits better:",
                "type": "proactive_suggestion",
                "products": alt_data,
                "reason": "Recovery Mode"
            }, "airdeliver.ai.response.out")

    async def _handle_initial_suggestions(self, user_id: int):
        time_context = self._get_time_context()
        logger.info(f"🌟 Generating {time_context} picks for User {user_id}")
        
        statement = select(Product).order_by(Product.rating.desc()).limit(60)
        candidates = (await self.db.exec(statement)).all()
        if not candidates: return

        weighted_candidates = []
        for p in candidates:
            cat = p.category.lower() if p.category else ""
            if time_context == "morning" and ("coffee" in cat or "office" in cat): 
                weighted_candidates.insert(0, p)
            elif time_context == "night" and ("game" in cat or "light" in cat): 
                weighted_candidates.insert(0, p)
            else: 
                weighted_candidates.append(p)

        selected = weighted_candidates[:8]
        random.shuffle(selected)
        products_data = [p.model_dump(mode='json') for p in selected]
        
        greeting_map = {
            "morning": "Good morning! ☀️  Your daily dose of inspiration has arrived.",
            "afternoon": "Good afternoon! ✨ Highlights from today, picked just for you.",
            "evening": "Good evening! 🌙 Relax and explore our most-loved items.",
            "night": "Welcome, night owl. 🌙🦉 Your exclusive late-night edit awaits."
        }

        await self.rabbitmq.publish({
            "user_id": user_id,
            "content": greeting_map.get(time_context, "Welcome back! Top picks for you:"),
            "type": "proactive_suggestion",
            "products": products_data,
            "reason": "Top Picks"
        }, "airdeliver.ai.response.out")

    # --- ⚙️ CORE PROCESSING (THE INTELLIGENCE ROUTER) ---

    async def _execute_strategic_search(self, strategy: Any, user_id: int) -> List[Product]:
        all_candidates = []
        for query in strategy.search_queries[:3]:
            try:
                results = await self.search_engine.perform_hybrid_search_pure(self.db, query)
                for prod in results:
                    if not any(p.id == prod.id for p in all_candidates):
                        all_candidates.append(prod)
            except Exception as e:
                logger.error(f"Strategy search sub-query failed: {e}")
        
        filtered = []
        for p in all_candidates:
            if strategy.price_max and p.price > strategy.price_max: continue
            if strategy.price_min and p.price < strategy.price_min: continue
            if strategy.category_filter:
                if not (strategy.category_filter.lower() in p.category.lower() or 
                        strategy.category_filter.lower() in (p.description or "").lower()):
                    continue
            filtered.append(p)
        return filtered

    async def process_message(self, message_payload: dict):
        user_id = message_payload.get("user_id")
        raw_message = message_payload.get("message")
        message_text = str(raw_message).strip() if raw_message else ""

        if not message_text: return

        if message_text.startswith("__INTERNAL_"):
            await self._process_internal_command(user_id, message_text)
            return

        if await self._handle_text_commands(user_id, message_text):
            return

        # 1. Strategy
        strategy = await self.llm_service.strategize_search(message_text)
        
        if strategy.search_queries and any(q in ["checkout", "confirm", "pay"] for q in strategy.search_queries):
             await self.rabbitmq.publish({**message_payload, "user_id": user_id}, "airdeliver.ai.intent.confirm_order")
             return

        # 2. Execution (Fetch Context)
        candidates = await self._execute_strategic_search(strategy, user_id)
        if not candidates:
            candidates = await self.search_engine.perform_hybrid_search_pure(self.db, message_text)

        # --- 🔥 DEEP RESEARCH & DISPLAY FIX (The Golden Logic) 🔥 ---
        is_informational_query = any(q in message_text.lower() for q in [
            "what is", "specs", "specifications", "details", "review", "vs", "compare", 
            "battery", "features", "ingredients", "info", "tell me about"
        ])
        
        if is_informational_query:
            # 1. Context Setup
            target_data = candidates[0].model_dump(mode='json') if candidates else {"name": message_text, "category": "General"}
            
            # 2. Consult External Knowledge
            expert_answer = await self.llm_service.consult_on_product(target_data, message_text)
            
            # 3. Step A: Send TEXT Answer (Guaranteed to show fully on original frontend)
            await self.rabbitmq.publish({
                "user_id": user_id,
                "content": expert_answer, 
                "type": "text" 
            }, "airdeliver.ai.response.out")

            # 4. Step B: Send Products Carousel (Separate message)
            if candidates:
                candidate_data = [p.model_dump(mode='json') for p in candidates[:5]]
                await asyncio.sleep(0.5) # Time for user to read text
                await self.rabbitmq.publish({
                    "user_id": user_id,
                    "content": "Based on your request, these are the closest matches:",
                    "type": "product_carousel",
                    "products": candidate_data,
                    "reason": "Research Matches"
                }, "airdeliver.ai.response.out")
            return
        # ------------------------------------------------

        # 4. Fallback
        if not candidates:
            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": f"I couldn't find a match for '{message_text}'. Try a different keyword or category.", 
                "type": "error"
            }, "airdeliver.ai.response.out")
            return

        # 5. Curation
        candidate_data = [p.model_dump(mode='json') for p in candidates[:15]]
        ai_curation = await self.llm_service.filter_and_recommend(
            user_query=message_text,
            products=candidate_data,
            tone_instruction=strategy.response_tone
        )

        final_display_products = []
        intro_message = strategy.direct_answer_prefix

        if ai_curation and ai_curation.selected_ids:
            intro_message = ai_curation.intro_message
            for p in candidate_data:
                if p['id'] in ai_curation.selected_ids:
                    p['ai_notes'] = ai_curation.reasoning.get(str(p['id']), "Perfect Match")
                    final_display_products.append(p)
        else:
            final_display_products = candidate_data[:5]
            
        await self._mark_products_as_seen(user_id, final_display_products)
        
        await self.rabbitmq.publish({
            "user_id": user_id,
            "content": intro_message,
            "type": "product_carousel",
            "products": final_display_products,
            "reason": "AI Selection"
        }, "airdeliver.ai.response.out")

    async def _process_internal_command(self, user_id: int, command: str):
        if command == "__INTERNAL_GET_INITIAL_SUGGESTIONS__":
            await self._handle_initial_suggestions(user_id)
            return

        if command == "__INTERNAL_RESET_SESSION__":
            cart_key = self._get_cart_key(user_id)
            seen_key = self._get_seen_key(user_id)
            await self.cache.delete(cart_key)
            await self.cache.delete(seen_key)
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": False}, "airdeliver.ai.intent.clear_cart")
            return

        if command == "__INTERNAL_SAVE_FOR_LATER__":
            await self.rabbitmq.publish({"user_id": user_id, "content": "Saved to wishlist. 💾", "type": "success_text"}, "airdeliver.ai.response.out")
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": False}, "airdeliver.ai.intent.clear_cart")
        elif command == "__INTERNAL_CLEAR_CART__":
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": True}, "airdeliver.ai.intent.clear_cart")
        
        elif command.startswith("__INTERNAL_ADD_BY_ID__:") and user_id:
            try:
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": pid, "quantity": 1}, "airdeliver.ai.intent.add_to_cart")
                p = await self.db.get(Product, pid)
                if p: 
                    await self.rabbitmq.publish({"user_id": user_id, "content": f"Added **{p.name}**. Anything else?", "type": "success_text"}, "airdeliver.ai.response.out")
                    asyncio.create_task(self._handle_secondary_suggestions(user_id, p))
                    await asyncio.sleep(0.5)
                    await self.rabbitmq.publish({"user_id": user_id, "content": "Ready to checkout?", "type": "confirmation_prompt", "options": ["Confirm Order", "Clear Cart"]}, "airdeliver.ai.response.out")
            except Exception: pass
            
        elif command.startswith("__INTERNAL_REMOVE_BY_ID__:") and user_id:
            try:
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": pid, "action": "remove_by_id"}, "airdeliver.ai.intent.remove_from_cart")
                asyncio.create_task(self._handle_removal_recovery(user_id, pid))
            except Exception: pass
