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

    async def _handle_image_query(self, user_id: int, image_data: str):
        """
        👁️ GLOBAL STANDARD V8: The 'Sensory' Vision Pipeline.
        Prioritizes Visual Attributes (Color, Material, Shape) over Price/Text popularity.
        If it looks Orange, it MUST be the Orange product.
        """
        if not image_data: return

        # 1. Feedback
        await self.rabbitmq.publish({"user_id": user_id, "content": "Analyzing Color & Design DNA... 👁️🎨", "type": "typing"}, "airdeliver.ai.response.out")

        # 2. Parallel Acquisition
        visual_task = self.search_engine.search_by_image_vector(image_data, limit=20) # Fetch more to filter by color
        analysis_task = self.llm_service.analyze_product_image(image_data)
        visual_matches, analysis_text = await asyncio.gather(visual_task, analysis_task)

        # ---------------------------------------------------------
        # 🎨 STAGE A: VISUAL ATTRIBUTE EXTRACTION (استخراج السمات)
        # ---------------------------------------------------------
        # We extract what the eye sees (Adjectives), not just nouns.
        analysis_lower = analysis_text.lower()
        
        # 1. Detect Colors (The most distinct visual feature)
        colors = ["orange", "gold", "titanium", "natural", "black", "white", "blue", "green", "pink", "purple", "silver", "desert", "copper"]
        detected_colors = [c for c in colors if c in analysis_lower]
        
        # 2. Detect Materials/Features
        features = ["pro", "max", "ultra", "triple", "camera", "ceramic", "glass", "leather", "silicone"]
        detected_features = [f for f in features if f in analysis_lower]

        # ---------------------------------------------------------
        # 🧠 STAGE B: THE ABSTRACT SEARCH
        # ---------------------------------------------------------
        # Remove "hallucinated" versions (14, 15) but KEEP the detected attributes
        import re
        clean_text = re.sub(r'iphone\s*\d+', 'iphone', analysis_lower) # Convert "iphone 15" -> "iphone"
        clean_text = re.sub(r'\b(looks like|similar to|possibly)\b', '', clean_text)
        
        # Construct a search query based on Visual Truth
        # Query = "iPhone Orange Titanium" (Forces DB to find this specific look)
        search_query = clean_text.split('.')[0] # Take the first sentence only
        if len(search_query) < 3: search_query = "item"

        # Search
        candidates = await self.search_engine.perform_hybrid_search_pure(self.db, search_query, limit=30)
        
        # Merge with vector results for safety
        if visual_matches:
            candidates.extend([p for p in visual_matches if p.id not in [c.id for c in candidates]])

        # ---------------------------------------------------------
        # ⚖️ STAGE C: THE SENSORY SCORING ENGINE (قلب الموازين)
        # ---------------------------------------------------------
        # Instead of sorting by Price, we sort by "Visual Fidelity".
        
        scored_candidates = []
        for p in candidates:
            score = 0

            tags_content = ""
            if p.tags:
                if isinstance(p.tags, list):
                    tags_content = " ".join([str(t) for t in p.tags]) # Join list items
                else:
                    tags_content = str(p.tags) # Convert to

            prod_text = (str(p.name) + " " + str(p.description or "") + " " + tags_content).lower()
            
            # Rule 1: Color Match is King (50 Points)
            # If AI saw "Orange", and product is "Orange", it wins instantly.
            for color in detected_colors:
                if color in prod_text:
                    score += 50
            
            # Rule 2: Feature Match (20 Points)
            # "Pro", "Max", "Titanium"
            for feat in detected_features:
                if feat in prod_text:
                    score += 20
            
            # Rule 3: Exact Name Match in Analysis (30 Points)
            # If AI said "Watch Ultra" and product is "Watch Ultra"
            clean_name_tokens = set(re.findall(r'\w+', p.name.lower()))
            analysis_tokens = set(re.findall(r'\w+', analysis_lower))
            overlap = len(clean_name_tokens.intersection(analysis_tokens))
            score += (overlap * 5)

            # Rule 4: Price Tie-Breaker (1 Point)
            # If two items have same visual score, pick the more expensive (likely newer)
            score += (p.price * 0.001)

            scored_candidates.append((p, score))

        # Sort by Score Descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        final_products = [item[0] for item in scored_candidates[:5]]

        # ---------------------------------------------------------
        # 🗣️ STAGE D: DISPLAY LOGIC
        # ---------------------------------------------------------
        # Name Generator logic (V6)
        display_name = "your item"
        if final_products:
            display_name = final_products[0].name # Use the winner's name

        msg = f"Closest match: {display_name}. You can add it to your cart when you're ready."

        # Dispatch
        if final_products:
            products_data = [p.model_dump(mode='json') for p in final_products]
            await self._mark_products_as_seen(user_id, products_data)
            
            if self.behavior_engine:
                 products_data = await self.behavior_engine.collapse_wavefunction(user_id, products_data)

            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": msg, 
                "type": "product_carousel", 
                "products": products_data, 
                "reason": "Sensory Intelligence"
            }, "airdeliver.ai.response.out")
        else:
            await self.rabbitmq.publish({
                "user_id": user_id, 
                "content": "I analyzed the visuals but couldn't find an exact style match in stock.", 
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
        Generates a message that feels like it knows you and the time.
        """
        import random
        
        # 1. Analyze the "Vibe" of the product
        # e.g. "Coffee" -> Energy, "Gaming" -> Fun, "Office" -> Focus
        vibe = "neutral"
        p_name = product.name.lower() if product else ""
        p_cat = (product.category or "").lower() if product else ""
        combined = p_name + " " + p_cat
        
        if any(x in combined for x in ["game", "console", "play", "rgb"]): vibe = "fun"
        elif any(x in combined for x in ["coffee", "brew", "energy", "sport"]): vibe = "energy"
        elif any(x in combined for x in ["office", "desk", "work", "laptop"]): vibe = "focus"
        elif any(x in combined for x in ["sleep", "bed", "relax", "candle"]): vibe = "chill"
        elif any(x in combined for x in ["phone", "tech", "smart", "watch"]): vibe = "tech"

        # 2. Template Matrix (Time x Vibe)
        # This creates the illusion of deep understanding.
        
        templates = {
            "morning": {
                "energy": ["Rise and shine! ☀️ Fuel up with these:", "Morning! Ready to conquer the day? Start here:", "Wakey wakey! ☕ Your morning essentials:"],
                "focus": ["Good morning. Let's get productive today:", "Morning! Gear up for a successful day:", "Ready to work? Here is your toolkit:"],
                "tech": ["Top of the morning! Check out today's tech drops:", "Morning! Smart choices for a smart day:"],
                "default": ["Good morning! ☀️ Here's what's trending for you:", "Morning! A fresh selection just for you:"]
            },
            "afternoon": {
                "energy": ["Mid-day slump? ⚡ Recharge with these:", "Power through your afternoon:"],
                "focus": ["Good afternoon. Keep the momentum going:", "Afternoon check-in! 🚀 Upgrades for your setup:"],
                "fun": ["Taking a break? 🎮 You deserve a treat:", "Afternoon vibes. Check these out:"],
                "default": ["Good afternoon! 👋 Picked specially for you:", "Hope your day is going well! Take a look:"]
            },
            "evening": {
                "chill": ["Long day? 🌙 Time to unwind:", "Good evening. Relax and explore:", "Evening vibes ✨ Comfort picks for you:"],
                "fun": ["Evening is here! Time to play:", "Good evening! Ready for some action?"],
                "kitchen": ["Dinner time? 🍽️ Inspiration for your evening:", "Good evening! Chef's choice for you:"],
                "default": ["Good evening! ✨ Highlights from today:", "Wrapping up the day with these picks:"]
            },
            "night": {
                "chill": ["Late night browsing? 🦉 We got you:", "Quiet hours. ✨ Explore our night edit:"],
                "fun": ["Night owl mode: ON. 🦉🎮 Gamers only:", "Up late? The best gear never sleeps:"],
                "default": ["Welcome, night owl. 🌙 Exclusive late-night finds:", "Burning the midnight oil? Check this:"]
            }
        }

        # 3. Select Template
        options = templates.get(time_phase, {}).get(vibe, templates[time_phase]["default"])
        
        # 4. Personalization Injection (If we used Ghost Vector)
        msg = random.choice(options)
        
        if stream == "GHOST":
            # Add a subtle nod that we know them
            suffixes = [" (Based on your style)", " (Matches your vibe)", " (Because you liked similar items)"]
            # We assume a 30% chance to append the suffix to keep it natural, not robotic
            if random.random() < 0.3:
                msg += random.choice(suffixes)
                
        return msg
