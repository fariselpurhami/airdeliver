# apps/api/app/services/ai_nlu_service.py

import logging
import asyncio
import random
import re
from datetime import datetime
from typing import List, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, and_
from sqlalchemy import func
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import IAsyncCacheClient
from app.services.free_llm_service import FreeLLMService
from app.models.product import Product
from app.models.order import Order
from app.models.enums import OrderStatus
from app.db.session import SessionLocal 

logger = logging.getLogger(__name__)

class AINLUService:
    """
    The Order With Air Brain (v25.0 - Platinum Standard).
    Central Intelligence Unit for processing Multimodal Intents (Text, Voice, Vision).
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

    # --- 👁️ VISION HANDLER (Architectural Component) ---
    async def _handle_image_query(self, user_id: int, image_data: str):
        if not image_data: return

        await self.rabbitmq.publish({"user_id": user_id, "content": "Analyzing visual signature... 👁️", "type": "typing"}, "airdeliver.ai.response.out")
        
        # 1. Vision Analysis (The AI tells us WHAT it is: "Shoe", "Car", "Phone")
        search_terms = await self.llm_service.analyze_product_image(image_data)
        
        # 2. Strict Search
        candidates = await self.search_engine.perform_hybrid_search_pure(self.db, search_terms, limit=10)
        
        # 3. The "Universal Smart Filter" Logic (V2 - Global Standard)
        exact_matches = []
        accessories = []
        
        # نستخرج الكلمات المفتاحية من بحث الـ AI
        # مثلاً لو البحث "iPhone 17"، الكلمات هي {"iphone", "17"}
        # لو البحث "Nike Jordan"، الكلمات هي {"nike", "jordan"}
        query_tokens = set(search_terms.lower().split())

        for p in candidates:
            prod_name = p.name.lower()
            
            # المنطق العالمي:
            # المنتج "المطابق" هو الذي يحتوي على كل كلمات البحث الرئيسية.
            # أي شيء آخر يعتبر "ملحق" أو "بديل".
            is_exact = all(token in prod_name for token in query_tokens)
            
            # تصفية إضافية: إذا كان الاسم يحتوي على كلمات تدل على "ملحق" (ديناميكي)
            # هذه القائمة يمكن توسيعها أو جعل الـ AI يحددها
            is_accessory_keyword = any(acc in prod_name for acc in ["case", "cover", "charger", "cable", "laces", "rims", "filter", "strap"])
            
            if is_exact and not is_accessory_keyword:
                exact_matches.append(p)
            else:
                accessories.append(p)

        # 4. Decision Matrix (نفس المنطق السابق لكن يعمل مع أي منتج)
        final_products = []
        response_msg = ""
        response_reason = ""

        if exact_matches:
            final_products = exact_matches
            response_msg = f"Visual Match Confirmed: Found {len(final_products)} matches for '{search_terms}'."
            response_reason = "Direct Visual Hit"
        
        elif not exact_matches and accessories:
            # هذا السيناريو يعمل الآن مع الأحذية (يعرض الأربطة) والسيارات (يعرض الإطارات)
            final_products = accessories[:5]
            response_msg = f"I couldn't find the exact '{search_terms}' in stock, but I found these related items/accessories:"
            response_reason = "Smart Alternative Suggestion"
            
        elif not exact_matches and not accessories:
            # Fallback
            fallback_terms = search_terms.split()[-1] 
            final_products = await self.search_engine.perform_hybrid_search_pure(self.db, fallback_terms, limit=5)
            response_msg = f"No exact match for '{search_terms}', but here are similar items from our collection:"
            response_reason = "Category Fallback"

        # ... (Display logic remains the same)
        if final_products:
            products_data = [p.model_dump(mode='json') for p in final_products]
            await self._mark_products_as_seen(user_id, products_data)
            await self.rabbitmq.publish({
                "user_id": user_id,
                "content": response_msg,
                "type": "product_carousel",
                "products": products_data,
                "reason": response_reason
            }, "airdeliver.ai.response.out")
        else:
             await self.rabbitmq.publish({
                "user_id": user_id,
                "content": f"Deep scan complete. '{search_terms}' is currently unavailable in the grid.",
                "type": "error"
            }, "airdeliver.ai.response.out")

    # --- 🧠 MAIN BRAIN PROCESSOR ---
    async def process_message(self, message_payload: dict):
        """
        The Central Nervous System. Routes messages based on Type and Intent.
        """
        user_id = message_payload.get("user_id")
        
        # ✅ CRITICAL FIX: Extract msg_type HERE, at the top level.
        msg_type = message_payload.get("type", "CHAT_MESSAGE")
        
        raw_message = message_payload.get("message")
        message_text = str(raw_message).strip() if raw_message else ""

        # --- 1. VISION FLOW PRIORITY ---
        if msg_type == "IMAGE_QUERY":
            image_data = message_payload.get("image")
            await self._handle_image_query(user_id, image_data)
            return # Exit immediately to prevent text fallback

        if not message_text: return

        # --- 2. INTERNAL COMMANDS ---
        if message_text.startswith("__INTERNAL_"):
            await self._process_internal_command(user_id, message_text)
            return

        # --- 3. TEXT COMMANDS (Clear, Checkout, etc.) ---
        if await self._handle_text_commands(user_id, message_text):
            return

        # --- 4. MEMORY EXTRACTION (Fire & Forget) ---
        async def _background_memorize():
            fact = await self.llm_service.extract_memory_worthy_facts(message_text)
            if fact:
                await self.search_engine.remember_user_fact(user_id, fact)
        asyncio.create_task(_background_memorize())

        # --- 5. SEARCH STRATEGY & MEMORY RECALL ---
        user_context_facts = await self.search_engine.recall_relevant_facts(user_id, message_text)
        context_str = f"USER CONTEXT (PRIORITY): {'; '.join(user_context_facts)}." if user_context_facts else ""
        augmented_query = f"{message_text} \n[SYSTEM_NOTE: {context_str}]" if context_str else message_text

        strategy = await self.llm_service.strategize_search(augmented_query)
        
        # Check for checkout intent in strategy
        if strategy.search_queries and any(q in ["checkout", "confirm", "pay"] for q in strategy.search_queries):
             await self.rabbitmq.publish({**message_payload, "user_id": user_id}, "airdeliver.ai.intent.confirm_order")
             return

        # --- 6. EXECUTE SEARCH ---
        candidates = await self._execute_strategic_search(strategy, user_id)
        if not candidates:
            candidates = await self.search_engine.perform_hybrid_search_pure(self.db, message_text)

        # --- 7. INFORMATIONAL QUERY CHECK ---
        is_informational_query = any(q in message_text.lower() for q in [
            "what is", "specs", "specifications", "details", "review", "vs", "compare", 
            "battery", "features", "ingredients", "info", "tell me about"
        ])
        
        if is_informational_query:
            target_data = candidates[0].model_dump(mode='json') if candidates else {"name": message_text, "category": "General"}
            expert_answer = await self.llm_service.consult_on_product(target_data, message_text)
            
            await self.rabbitmq.publish({
                "user_id": user_id,
                "content": expert_answer, 
                "type": "text" 
            }, "airdeliver.ai.response.out")

            if candidates:
                candidate_data = [p.model_dump(mode='json') for p in candidates[:5]]
                await asyncio.sleep(0.5) 
                await self.rabbitmq.publish({
                    "user_id": user_id,
                    "content": "Based on your request, these are the closest matches:",
                    "type": "product_carousel",
                    "products": candidate_data,
                    "reason": "Research Matches"
                }, "airdeliver.ai.response.out")
            return

        # --- 8. NO RESULTS HANDLING ---
        if not candidates:
            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": f"I couldn't find a match for '{message_text}'. Try a different keyword or category.", 
                "type": "error"
            }, "airdeliver.ai.response.out")
            return

        # --- 9. AI CURATION & RESPONSE ---
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

    # --- HELPERS & LOGIC ---

    async def _handle_text_commands(self, user_id: int, text: str) -> bool:
        clean_text = text.lower().strip()
        
        if any(x in clean_text for x in ["clear cart", "empty cart", "delete all", "remove all"]):
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": True}, "airdeliver.ai.intent.clear_cart")
            return True
            
        if any(x in clean_text for x in ["checkout", "pay now", "confirm order", "finish order"]):
            await self.rabbitmq.publish({"user_id": user_id, "content": {}, "type": "payment_intent"}, "airdeliver.ai.intent.confirm_order")
            return True

        if clean_text in ["reset", "start over", "restart", "help"]:
            await self._process_internal_command(user_id, "__INTERNAL_RESET_SESSION__")
            await self._handle_initial_suggestions(user_id)
            return True

        return False

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
                    await self.rabbitmq.publish({"user_id": user_id, "content": f"Added '{p.name}' to your cart.", "type": "success_text"}, "airdeliver.ai.response.out")
                    suggestions_sent = await self._handle_secondary_suggestions(user_id, p.id)
                    await asyncio.sleep(0.8 if suggestions_sent else 0.3)
                    await self.rabbitmq.publish({"user_id": user_id, "content": "Ready to checkout?", "type": "confirmation_prompt", "options": ["Confirm Order", "Clear Cart"]}, "airdeliver.ai.response.out")
            except Exception as e: 
                logger.error(f"Error in internal add: {e}")
            
        elif command.startswith("__INTERNAL_REMOVE_BY_ID__:") and user_id:
            try:
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish({"user_id": user_id, "product_id": pid, "action": "remove_by_id"}, "airdeliver.ai.intent.remove_from_cart")
                await self._handle_removal_recovery(user_id, pid)
            except Exception: pass

    # --- BACKGROUND TASKS (Isolated Sessions) ---

    async def _handle_secondary_suggestions(self, user_id: int, product_id: int):
        async def _safe_bg_logic():
            async with SessionLocal() as bg_db:
                try:
                    added_product = await bg_db.get(Product, product_id)
                    if not added_product: return False

                    final_products = []
                    suggestion_reason = ""

                    # 1. Strategy: Smart Bundle (High Price Items)
                    if added_product.price > 150:
                        bundle_items = await self.search_engine.generate_smart_bundle(bg_db, added_product)
                        if bundle_items:
                            final_products = [p.model_dump(mode='json') for p in bundle_items[:5]]
                            suggestion_reason = f"🔥 Complete your setup! {added_product.name} works best with:"

                    # 2. Strategy: Semantic Complementary (Accessories)
                    if not final_products:
                        comps = await self.search_engine.find_complementary_products(bg_db, added_product, limit=5)
                        if comps:
                            final_products = [p.model_dump(mode='json') for p in comps[:5]]
                            suggestion_reason = f"💡 Essential add-ons for your {added_product.name}:"

                    # 3. Strategy: Category Best Sellers (Fallback A)
                    # [FIXED LOGIC HERE]
                    if not final_products and added_product.category:
                        statement = (
                            select(Product)
                            .where(Product.category == added_product.category)
                            .where(Product.id != added_product.id)
                            .order_by(Product.rating.desc())
                            .limit(5)
                        )
                        cat_best = (await bg_db.exec(statement)).all()
                        if cat_best:
                            final_products = [p.model_dump(mode='json') for p in cat_best]
                            suggestion_reason = f"🏆 Top rated in {added_product.category}:"

                    # 4. Strategy: Global Trending (Fallback B - Last Resort)
                    if not final_products:
                       statement = (
                           select(Product)
                           .where(Product.id != added_product.id)
                           .order_by(Product.rating.desc())
                           .limit(5)
                       )
                       global_best = (await bg_db.exec(statement)).all()
                       if global_best:
                          final_products = [p.model_dump(mode='json') for p in global_best]
                          suggestion_reason = "✨ Popular choices you might like:"

                    # 5. Final Dispatch
                    if final_products:
                        await self._mark_products_as_seen(user_id, final_products)
                        await self.rabbitmq.publish({
                            "user_id": user_id,
                            "content": suggestion_reason,
                            "type": "proactive_suggestion",
                            "products": final_products,
                            "reason": "Smart Suggestion"
                        }, "airdeliver.ai.response.out")
                        return True

                    return False

                except Exception as e:
                    logger.error(f"Background suggestion error: {e}")
                    return False

        # Execute the wrapper
        return await _safe_bg_logic()

    async def _handle_removal_recovery(self, user_id: int, product_id: int):
        async def _safe_recovery():
            async with SessionLocal() as bg_db:
                try:
                    removed_product = await bg_db.get(Product, product_id)
                    if not removed_product: return

                    alternatives = await self.search_engine.perform_hybrid_search_pure(
                        bg_db,
                        f"alternative to {removed_product.name} {removed_product.category}",
                        limit=5
                    )
                    alternatives = [p for p in alternatives if p.id != product_id][:3]

                    if alternatives:
                        alt_data = [p.model_dump(mode='json') for p in alternatives]
                        await self.rabbitmq.publish({
                            "user_id": user_id,
                            "content": f"Changed your mind about '{removed_product.name}'? Maybe one of these fits better:",
                            "type": "proactive_suggestion",
                            "products": alt_data,
                            "reason": "Recovery Mode"
                        }, "airdeliver.ai.response.out")
                except Exception as e:
                    logger.error(f"Background recovery error: {e}")
        asyncio.create_task(_safe_recovery())

    async def _handle_initial_suggestions(self, user_id: int):
        time_context = self._get_time_context()
        is_morning_routine = (time_context == "morning")

        if is_morning_routine:
             routine_products = await self.search_engine.perform_hybrid_search_pure(self.db, "Coffee Beans Espresso", limit=2)
             if routine_products:
                 products_data = [p.model_dump(mode='json') for p in routine_products]
                 await self.rabbitmq.publish({
                    "user_id": user_id,
                    "content": "Good morning! ☀️ I've prepared your usual caffeine fix. Want me to add these to your cart?",
                    "type": "proactive_suggestion",
                    "products": products_data,
                    "reason": "Routine Detected ��"
                 }, "airdeliver.ai.response.out")
                 return

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
            "morning": "Good morning! ☀️ ✨ Your daily dose of inspiration has arrived.",
            "afternoon": "Good afternoon! 🌙  Highlights from today, picked just for you.",
            "evening": "Good evening! ✨ Relax and explore our most-loved items.",
            "night": "Welcome, night owl. 🦉 Your exclusive late-night edit awaits."
        }

        await self.rabbitmq.publish({
            "user_id": user_id,
            "content": greeting_map.get(time_context, "Welcome back! Top picks for you:"),
            "type": "proactive_suggestion",
            "products": products_data,
            "reason": "Top Picks"
        }, "airdeliver.ai.response.out")
