# apps/api/app/services/ai_nlu_service.py

import re
from sentence_transformers import util
from app.services.ai_commerce_engine import ai_manager  
from app.services.ai_behavior_engine import BehaviorEngine # ✅ Add Import
import logging
import asyncio
import random
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

try:
    from ddgs import DDGS # New style
except ImportError:
    try:
        from duckduckgo_search import DDGS # Old/Standard style
    except ImportError:
        DDGS = None # Fa

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
        behavior_engine: BehaviorEngine = None
    ):
        self.db = db 
        self.search_engine = search_engine
        self.rabbitmq = rabbitmq
        self.cache = cache
        self.llm_service = llm_service
        self.behavior_engine = behavior_engine
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

    async def _perform_external_verification(self, image_desc: str) -> str:
        """
        🌍 V18: THE SMART LIVE AGENT (With Garbage Filter).
        It searches the web, BUT it rejects anything that looks like a blog, a list, or a tool.
        It ONLY returns a result if it looks like a real "Model Name".
        """
        if not DDGS: return ""

        try:
            # We refine the query to ask for a specific model identification
            query = f"what is the exact model name of this product: {image_desc}"
            
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: list(DDGS().text(query, max_results=4))
            )
            
            if not results: return ""

            # 🛡️ THE GARBAGE FILTER (فلتر القمامة)
            # These words indicate the result is NOT a product name, but a generic page.
            # 🛡️ THE GARBAGE FILTER (فلتر القمامة الموسع)
            junk_indicators = [
                "best", "top 10", "guide", "review", "vs", "versus", "compare", 
                "finder", "tool", "analysis", "free", "download", "list", 
                "cheap", "deal", "amazon", "ebay", "shop", "price", "stock",
                "image", "search", "google", "bing", "yandex", "wiki",
                "how to", "tutorial", "video", "forum", "reddit", "login"
            ]
            
            valid_name = ""
            
            for res in results:
                title = res['title']
                
                # 1. Clean the title
                # Remove common suffixes like " - Official Site", " - Wikipedia"
                import re
                clean_title = re.sub(r'(\s-|\|).+', '', title).strip()
                
                # 2. Check for Junk
                if any(bad in clean_title.lower() for bad in junk_indicators):
                    continue # Skip this result, it's trash
                
                # 3. Validation Heuristic (The Genius Check)
                # A real product name is usually short (2-6 words)
                # e.g. "Sony WH-1000XM5" (Good) vs "How to find the best headphones" (Bad)
                word_count = len(clean_title.split())
                if 2 <= word_count <= 7:
                    valid_name = clean_title
                    break # We found a clean candidate!
            
            if valid_name:
                logger.info(f"🌍 Live Agent Verified: '{valid_name}' (Clean Match)")
                return valid_name
            else:
                logger.warning("🌍 Live Agent found only generic/junk results. Switching to Internal Vision.")
                return ""

        except Exception as e:
            logger.warning(f"🌍 Live Search failed: {e}")
            return ""

    async def _handle_image_query(self, user_id: int, image_data: str):
        """
        💎 GLOBAL STANDARD V17: The 'Universal Masterpiece'.
        A category-agnostic pipeline that adapts its strategy based on what it sees.
        
        STRATEGY SWITCHER:
        1. If it's a specific model (Tech/Cars/Branded) -> Uses LIVE WEB SEARCH + SNIPER DB.
        2. If it's a generic item (Food/Furniture/Clothes) -> Uses SEMANTIC CROSS-ENCODING.
        
        Zero Bias. Works for everything.
        """
        if not image_data: return

        await self.rabbitmq.publish({"user_id": user_id, "content": "Analyzing Object DNA & World Context... 👁️🌍", "type": "typing"}, "airdeliver.ai.response.out")

        # 1. ACQUIRE DEEP INTELLIGENCE
        visual_task = self.search_engine.search_by_image_vector(image_data, limit=50) 
        analysis_task = self.llm_service.analyze_product_image(image_data)
        visual_matches, analysis_text = await asyncio.gather(visual_task, analysis_task)
        
        analysis_lower = analysis_text.lower()

        # ---------------------------------------------------------
        # 🌍 PHASE 1: THE LIVE IDENTIFICATION (للمنتجات ذات الهوية)
        # ---------------------------------------------------------
        # Check if the analysis suggests a Specific Brand/Model or just a Generic Item.
        # "Apple Watch" -> Specific. "Red wooden chair" -> Generic.
        
        is_specific_entity = any(x in analysis_lower for x in ["model", "brand", "edition", "series", "version", "release"])
        
        exact_name_from_web = ""
        if is_specific_entity:
            # Use the Live Internet Agent to find the real world name
            # This works for "iPhone 17" as well as "Nike Air Jordan 5" or "Sony A7 Camera"
            exact_name_from_web = await self._perform_external_verification(analysis_text[:200])

        # ---------------------------------------------------------
        # 🧠 PHASE 2: THE ADAPTIVE SEARCH (البحث المتكيف)
        # ---------------------------------------------------------
        candidates = []
        search_strategy = ""

        # STRATEGY A: SNIPER (For recognized models)
        if exact_name_from_web:
            logger.info(f"🎯 Strategy A (Sniper): Hunting for '{exact_name_from_web}'")
            # Search for the EXACT name found on the web
            candidates = await self.search_engine.perform_hybrid_search_pure(self.db, exact_name_from_web, limit=20)
            search_strategy = "Sniper"
        
        # STRATEGY B: SEMANTIC (For generic items or if Sniper missed)
        if not candidates:
            logger.info("🌊 Strategy B (Semantic): Falling back to descriptive search.")
            # Remove "I see", "Image shows" noise
            import re
            clean_desc = re.sub(r'(Image shows|I see|looks like|appears to be)', '', analysis_text, flags=re.IGNORECASE).strip()
            # Use the first 10 meaningful words
            search_query = " ".join(clean_desc.split()[:10])
            candidates = await self.search_engine.perform_hybrid_search_pure(self.db, search_query, limit=50)
            search_strategy = "Semantic"

        # Merge visual vector matches (The "Shape" backup)
        if visual_matches:
            existing_ids = {c.id for c in candidates}
            for vm in visual_matches:
                if vm.id not in existing_ids: candidates.append(vm)

        # ---------------------------------------------------------
        # ⚖️ PHASE 3: THE UNIVERSAL SCORING ENGINE (الترتيب العالمي)
        # ---------------------------------------------------------
        scored_candidates = []
        text_model = ai_manager.get_text_model()
        
        # We encode the 'Analysis' as the anchor truth
        anchor_emb = text_model.encode(analysis_lower, convert_to_tensor=True)
        
        # Extract Universal Attributes (Color/Material) from Analysis
        # Note: We don't hardcode colors list anymore, we rely on semantic similarity for colors,
        # BUT we boost if we find exact word matches for robustness.
        common_colors = ["red", "blue", "green", "black", "white", "silver", "gold", "yellow", "orange", "brown", "pink", "purple", "grey", "beige"]
        detected_colors = [c for c in common_colors if c in analysis_lower]

        for p in candidates:
            # Prepare Product DNA
            # Safe Tag handling included
            tags_str = " ".join([str(t) for t in p.tags]) if isinstance(p.tags, list) else str(p.tags or "")
            prod_dna = f"{p.name} {p.category or ''} {p.description or ''} {tags_str}".lower()
            
            # 1. Semantic Similarity (0-100) - Works for EVERYTHING
            prod_emb = text_model.encode(prod_dna, convert_to_tensor=True)
            sem_score = util.cos_sim(anchor_emb, prod_emb).item() * 100
            
            # 2. The "Web Truth" Boost (If we found a name online)
            if exact_name_from_web and exact_name_from_web.lower() in prod_dna:
                sem_score += 500.0 # Huge boost if it matches the web result
            
            # 3. Universal Attribute Enforcement
            # If AI saw "Red", and Product has "Red", boost it.
            for color in detected_colors:
                if color in prod_dna:
                    sem_score += 50.0
            
            # 4. Price Logic (Contextual)
            # If the description sounds expensive (Luxury, Pro, Gold), prefer higher price
            if any(w in analysis_lower for w in ["luxury", "expensive", "premium", "pro", "ultra", "gold"]):
                sem_score += (p.price * 0.05)
            
            scored_candidates.append((p, sem_score))

        # Sort
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        final_list = scored_candidates[:5]
        final_products = [item[0] for item in final_list]

        # ---------------------------------------------------------
        # 🗣️ PHASE 4: THE ADAPTIVE DISPATCH
        # ---------------------------------------------------------
        if final_products:
            display_name = final_products[0].name
            import random
            
            msg = ""
            # Message adapts based on CONFIDENCE
            top_score = final_list[0][1] if final_list else 0
            
            if top_score > 400: # We had a Web Match or Super Semantic Match
                templates = [
                    f"Identified: {display_name}. Found in stock.",
                    f"That looks like the {display_name}. Here it is:",
                    f"Match confirmed: {display_name}."
                ]
                msg = random.choice(templates)
            else:
                # Lower confidence (Generic items)
                msg = f"Closest match: {display_name}. You can add it to your cart when you're ready."

            # Color warning if semantic score wasn't perfect but model matched
            if top_score < 400 and top_score > 100: 
                 msg += " (Note: Exact color/variant might differ)."

            products_data = [p.model_dump(mode='json') for p in final_products]
            await self._mark_products_as_seen(user_id, products_data)
            
            if self.behavior_engine:
                 products_data = await self.behavior_engine.collapse_wavefunction(user_id, products_data)

            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": msg, 
                "type": "product_carousel", 
                "products": products_data, 
                "reason": f"Universal Intelligence ({search_strategy})"
            }, "airdeliver.ai.response.out")
        else:
            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": f"I analyzed the object, but couldn't find a close match in our inventory.", 
                "type": "error"
            }, "airdeliver.ai.response.out")

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
        
        if self.behavior_engine and final_display_products:
            # نتأكد أن القائمة ليست فارغة وأن المحرك موجود
            logger.info(f"🔮 Collapsing Wavefunction for User {user_id}...")
            final_display_products = await self.behavior_engine.collapse_wavefunction(
                user_id,
                final_display_products
            )
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
            await self.rabbitmq.publish({"user_id": user_id, "content": "Saved to wishlist. ��", "type": "success_text"}, "airdeliver.ai.response.out")
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
        """
        🧬 GLOBAL STANDARD V3: The 'Orthogonal' Completion Engine.
        Strictly bans the anchor category to enforce ACCESSORY suggestions.
        """
        async def _safe_bg_logic():
            async with SessionLocal() as bg_db:
                try:
                    anchor_product = await bg_db.get(Product, product_id)
                    if not anchor_product: return False

                    # 1. Define the Search Strategy (The Shift)
                    # We explicitly look for "Accessories" and "Parts"
                    queries = [
                        f"accessories for {anchor_product.name}",
                        f"case for {anchor_product.name}", # Specific for phones
                        f"compatible with {anchor_product.name}"
                    ]
                    
                    raw_candidates = []
                    for q in queries:
                        res = await self.search_engine.perform_hybrid_search_pure(bg_db, q, limit=30)
                        raw_candidates.extend(res)

                    final_bundle = []
                    seen_ids = {anchor_product.id}
                    anchor_cat = (anchor_product.category or "").lower()
                    
                    # 2. THE STRICT FILTER (The "Anti-Echo" Logic)
                    for p in raw_candidates:
                        if p.id in seen_ids: continue
                        if len(final_bundle) >= 4: break

                        p_cat = (p.category or "").lower()
                        
                        # 🚫 BAN RULE 1: SAME CATEGORY BLOCK
                        # If I bought a Phone, DO NOT show me a Phone.
                        # Exception: Unless the candidate is drastically cheaper (< 20% price), likely a spare part.
                        if p_cat == anchor_cat and p.price > (anchor_product.price * 0.2):
                            continue # Block it.

                        # 🚫 BAN RULE 2: PRICE CEILING
                        # Accessories shouldn't cost more than the main item.
                        if p.price > anchor_product.price:
                            continue

                        final_bundle.append(p)
                        seen_ids.add(p.id)

                    # 3. Dispatch
                    if final_bundle:
                        products_data = [p.model_dump(mode='json') for p in final_bundle]
                        # ... (نفس كود الإرسال السابق) ...
                        await self.rabbitmq.publish({
                            "user_id": user_id,
                            "content": f"Complete your {anchor_product.name} setup with these:",
                            "type": "proactive_suggestion",
                            "products": products_data,
                            "reason": "Smart Completion"
                        }, "airdeliver.ai.response.out")
                        return True
                    return False
                except Exception: return False
        
        asyncio.create_task(_safe_bg_logic())


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
        """
        💎 THE ENDGAME ALGORITHM (With Human Touch).
        Combines Ghost Vectors, Context, and a Dynamic Persona Engine.
        """
        # 1. Context Acquisition
        time_context = self._get_time_context() # morning, afternoon, evening, night
        candidates = []
        source_stream = "" # "GHOST" or "TIME" or "EXPLORE"
        
        # --- STREAM A: THE GHOST VECTOR (Hyper-Personalization) ---
        has_personalized = False
        if self.behavior_engine:
            try:
                ghost_json = await self.cache.get(f"u:{user_id}:ghost_v2")
                if ghost_json:
                    import json
                    ghost_data = json.loads(ghost_json)
                    pos_vector = ghost_data.get('pos')
                    
                    if pos_vector:
                        vector_results = await self.search_engine._search_milvus(pos_vector, limit=15)
                        if vector_results:
                            product_ids = [int(pid) for pid, score in vector_results]
                            candidates = await self.search_engine._fetch_products_by_ids(product_ids)
                            source_stream = "GHOST"
                            has_personalized = True
            except Exception: pass

        # --- STREAM B: TEMPORAL PROBABILITY (Context Fallback) ---
        if not candidates or len(candidates) < 5:
            source_stream = "TIME"
            time_weights = {
                "morning":  {"Coffee": 50, "Breakfast": 30, "Wellness": 10, "Tech": 10},
                "afternoon": {"Office": 40, "Snack": 30, "Gadget": 20, "Accessories": 10},
                "evening":  {"Kitchen": 30, "Home Decor": 30, "Relax": 20, "Fitness": 20},
                "night":    {"Gaming": 40, "Lighting": 30, "Sleep": 20, "Reading": 10}
            }
            current_weights = time_weights.get(time_context, {"Trending": 100})
            
            import random
            selected_category = random.choices(list(current_weights.keys()), weights=list(current_weights.values()), k=1)[0]
            
            context_results = await self.search_engine.perform_hybrid_search_pure(self.db, selected_category, limit=10)
            candidates.extend(context_results)

        # --- STREAM C: STOCHASTIC EXPLORATION ---
        try:
            wildcard_term = random.choice(["New Arrival", "Best Seller", "Limited Edition"])
            wildcard_items = await self.search_engine.perform_hybrid_search_pure(self.db, wildcard_term, limit=2)
            if wildcard_items: candidates.insert(1, wildcard_items[0])
        except Exception: pass

        # --- FINAL PROCESSING ---
        unique_candidates = {p.id: p for p in candidates}.values()
        final_list = list(unique_candidates)
        
        if self.behavior_engine and final_list:
             final_list = await self.behavior_engine.collapse_wavefunction(user_id, final_list)
        
        final_display = final_list[:8]

        # 4. 🗣️ THE NARRATIVE ENGINE (توليد الكلام البشري)
        # We look at the FIRST product to determine the "Vibe" of the collection
        lead_product = final_display[0] if final_display else None
        
        human_message = self._craft_human_message(time_context, source_stream, lead_product)

        # Dispatch
        if final_display:
            products_data = [p.model_dump(mode='json') for p in final_display]
            
            await self.rabbitmq.publish({
                "user_id": user_id,
                "content": human_message, # <--- الرسالة الذكية هنا
                "type": "proactive_suggestion",
                "products": products_data,
                "reason": "AI Context Awareness"
            }, "airdeliver.ai.response.out")

    # ---------------------------------------------------------
    # 🧠 NEW HELPER: THE PERSONA GENERATOR
    # ---------------------------------------------------------
    def _craft_human_message(self, time_phase: str, stream: str, product: Any) -> str:
        """
        Generates a warm, expressive, and human-like English greeting.
        Adapts to time of day and product vibe with emotional intelligence.
        """
        import random
        
        # 1. Analyze the "Vibe"
        vibe = "neutral"
        p_name = product.name.lower() if product else ""
        p_cat = (product.category or "").lower() if product else ""
        combined = p_name + " " + p_cat
        
        if any(x in combined for x in ["game", "console", "play", "rgb"]): vibe = "fun"
        elif any(x in combined for x in ["coffee", "brew", "energy", "sport"]): vibe = "energy"
        elif any(x in combined for x in ["office", "desk", "work", "laptop", "monitor"]): vibe = "focus"
        elif any(x in combined for x in ["sleep", "bed", "relax", "candle", "sofa"]): vibe = "chill"
        elif any(x in combined for x in ["phone", "tech", "smart", "watch"]): vibe = "tech"

        # 2. THE EMOTIONAL ENGLISH MATRIX 🇺��
        
        templates = {
            "morning": {
                "energy": [
                    "Rise and shine! ☀️ Ready to conquer the day? Start here:",
                    "Good morning! ☕ Fuel up your ambition with these picks:",
                    "Wakey wakey! 🌅 Here is the energy boost you need:"
                ],
                "focus": [
                    "Good morning. �� Let's make today productive:",
                    "Morning! 🚀 Gear up for success with these essentials:",
                    "Ready to work? 🧠 Here is your toolkit for the day:"
                ],
                "tech": [
                    "Top of the morning! ⚡ Check out today's freshest tech:",
                    "Good morning! 📱 Smart choices for a smart start:"
                ],
                "default": [
                    "Good morning! ☀️ Wishing you a wonderful day ahead:",
                    "Hello there! 👋 A fresh selection just for you this morning:"
                ]
            },
            "afternoon": {
                "energy": [
                    "Mid-day slump? ⚡ Recharge your afternoon with this:",
                    "Hey there! 🌈 Keep the momentum going with these:"
                ],
                "focus": [
                    "Good afternoon. 🕑 Stay in the zone with these upgrades:",
                    "Checking in! 🚀 Everything you need to finish strong:"
                ],
                "fun": [
                    "Need a break? 🎮 You deserve a little treat right now:",
                    "Afternoon vibes! 🎈 Take a moment to explore these:"
                ],
                "default": [
                    "Good afternoon! 👋 Hope your day is going great:",
                    "Hello again! ✨ Hand-picked suggestions for your afternoon:"
                ]
            },
            "evening": {
                "chill": [
                    "Long day? 🌙 Time to unwind and relax:",
                    "Good evening. 🍷 You earned some downtime with these:",
                    "Evening vibes. ✨ create your cozy sanctuary:"
                ],
                "kitchen": [
                    "Dinner time? 🍽️ Inspiration for a delicious evening:",
                    "Good evening! ✨ Chef's choice for your home:"
                ],
                "default": [
                    "Good evening! 🌇 Wrapping up the day with these highlights:",
                    "Hello! �� A quiet browse through our latest collection:"
                ]
            },
            "night": {
                "chill": [
                    "Late night browsing? 🦉 We've got you covered:",
                    "Quiet hours. 🤫 Explore our peaceful night edit:",
                    "Welcome, night owl. 🌙 Serenity is just a click away:"
                ],
                "fun": [
                    "Night owl mode: ON. 🦉🎮 The best gear never sleeps:",
                    "Up late? 🚀 Level up your game while the world sleeps:"
                ],
                "default": [
                    "Burning the midnight oil? 🕯️ Check these out:",
                    "Hello. ✨ Exclusive late-night finds just for you:"
                ]
            }
        }

        # 3. Select Template
        options = templates.get(time_phase, {}).get(vibe, templates[time_phase]["default"])
        msg = random.choice(options)
        
        # 4. Subtle Personalization (The "I Know You" Touch)
        if stream == "GHOST":
            suffixes = [
                " (Picked for your style ✨)", 
                " (Matches your vibe 🎯)", 
                " (Because you have great taste 😉)"
            ]
            if random.random() < 0.4:
                msg += random.choice(suffixes)
                
        return msg
