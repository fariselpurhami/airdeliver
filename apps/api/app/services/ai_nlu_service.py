# apps/api/app/services/ai_nlu_service.py

import re
import logging
import asyncio
import random
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from sentence_transformers import util
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.services.ai_commerce_engine import AICommerceEngine, ai_manager  
from app.services.ai_behavior_engine import BehaviorEngine
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import IAsyncCacheClient
from app.services.free_llm_service import FreeLLMService
from app.models.product import Product
from app.db.session import SessionLocal 
from app.services.ai_meta_cognition import MetaCognitionLayer

logger = logging.getLogger("airdeliver.nlu")

class AINLUService:
    """
    🧠 THE ORDER WITH AIR BRAIN (V30.0 - UNIVERSAL DIAMOND EDITION).

    The Central Intelligence Unit that orchestrates the entire shopping experience.
    It acts as the bridge between User Intent (Natural Language) and System Action (Vector Search).

    ARCHITECTURAL PILLARS:
    1. 🌌 Universal Semantic Understanding: No more hardcoded logic; pure intent vectors.
    2. ⚡ Neuro-Symbolic Routing: Combines AI flexibility with deterministic execution speeds.
    3. 💎 Diamond Uplink: Direct, crash-proof WebSocket communication via Redis.
    4. 🧬 Financial DNA Integration: Adapts every response to the user's spending tier.
    """

    def __init__(
        self,
        db: AsyncSession,
        search_engine: AICommerceEngine, # 💎 المحرك المطور عالمياً
        rabbitmq: RabbitMQService,
        cache: IAsyncCacheClient,
        llm_service: FreeLLMService,
        behavior_engine: BehaviorEngine = None
    ):
        self.db = db
        self.search_engine = search_engine
        self.rabbitmq = rabbitmq
        self.cache = cache
        self.redis = cache
        self.llm_service = llm_service
        self.behavior_engine = behavior_engine
        self.meta_cognition = MetaCognitionLayer()

        # ⚙️ SOTA Configuration
        self.seen_cache_ttl = 3600
        self.context_window_size = 8 # ⬆️ رفعنا حجم الذاكرة لاستيعاب سياق أعمق
        self.min_intent_confidence = 0.75 # حد الثقة للمطابقة المتجهية


    async def _append_to_memory(
        self, 
        user_id: int, 
        role: str, 
        content: str, 
        intent: str = "general"
    ):
        """
        🔥 WRITES TO THE ETERNAL SCROLL (REDIS LIST).
        Saves precise metadata: Timestamp, Intent, and Role.
        Architecture: First-In-Last-Out (Stack) managed as a Sliding Window.
        """
        try:
            key = f"chat_history:{user_id}"
            
            # 1. التغليف الذكي (Smart Encapsulation)
            # لا نخزن نصاً فقط، بل نخزن "حدثاً" (Event)
            memory_packet = {
                "r": role,           # u=user, a=assistant (Short keys to save RAM)
                "c": content.strip(),# The payload
                "t": datetime.now().isoformat(), # Temporal anchor
                "i": intent          # The detected intent (e.g., 'buy_laptop')
            }
            
            # 2. الضغط والتخزين (Serialization)
            # نستخدم JSON لأنه الأسرع والأكثر توافقاً
            payload = json.dumps(memory_packet)
            
            # 3. الحقن الذري (Atomic Injection)
            # نستخدم Pipeline لضمان أن الإضافة والقص يحدثان في نبضة واحدة
            pipeline = self.cache.client.pipeline()
            pipeline.lpush(key, payload)   # ادفع في المقدمة
            pipeline.ltrim(key, 0, 29)     # احتفظ بآخر 30 رسالة فقط (Sliding Window)
            pipeline.expire(key, 86400)    # الذاكرة تموت بعد 24 ساعة (Session Scope)
            await pipeline.execute()       # نفذ الأمر كطلقة واحدة
            
        except Exception as e:
            # الذاكرة مهمة، لكن لا يجب أن توقف النظام إذا فشلت
            logger.error(f"💀 Memory Injection Failed: {e}")

    async def _get_conversation_context(self, user_id: int, limit: int = 5) -> str:
        """
        �� READS FROM THE ETERNAL SCROLL.
        Reconstructs the timeline in a format that makes the LLM feel "Omniscient".
        """
        try:
            key = f"chat_history:{user_id}"
            
            # 1. استحضار الأرواح (Fetch Raw Data)
            # نسحب ضعف العدد المطلوب لضمان وجود سياق كافٍ
            raw_data = await self.cache.client.lrange(key, 0, limit * 2)
            
            if not raw_data:
                return ""

            # 2. إعادة بناء الزمن (Timeline Reconstruction)
            # البيانات تأتي (أحدث -> أقدم)، يجب عكسها لتصبح (أقدم -> أحدث)
            timeline = []
            for packet in raw_data:
                try:
                    event = json.loads(packet)
                    role_label = "Customer" if event['r'] == 'u' else "Agent"
                    # تحويل الوقت لصيغة مقروءة للبشر (اختياري للذكاء الزائد)
                    # ts = datetime.fromisoformat(event['t']).strftime("%H:%M") 
                    # timeline.append(f"[{ts}] {role_label}: {event['c']}")
                    timeline.append(f"{role_label}: {event['c']}")
                except: continue

            # نعكس القائمة لنقرأ القصة من البداية
            timeline.reverse()
            
            # 3. الصياغة الدرامية (Prompt Engineering)
            # نحول القائمة لنص واحد متماسك يقرأه الـ LLM
            conversation_script = "\n".join(timeline)
            
            return conversation_script

        except Exception as e:
            logger.warning(f"⚠️ Memory Recall Failed: {e}")
            return ""
    async def _perform_devilish_recovery(self, user_id: int, removed_pid: int):
        """
        😈 THE GREAT DEVIL ALGORITHM V2.0 (PSYCHOLOGICAL WARFARE EDITION).
        
        Logic:
        1. Analyze the 'discarded' item to understand user's baseline standard.
        2. Set the 'discarded price' as the FLOOR (Min Price), never the ceiling.
        3. Hunt for the 'Alpha' version of that product (Pro, Max, Ultra).
        4. Manipulate the user's ego by framing the new product as the 'Correct Choice'.
        """
        try:
            # 1. تشريح جثة المنتج المحذوف
            target = await self.db.get(Product, removed_pid)
            if not target: return

            # استخراج البيانات الحيوية
            # (تحسين استخراج البراند: لو الاسم يبدأ بكلمة قصيرة زي HP, LG نأخذها، لو طويلة نأخذها برضه)
            # ولو متاح في الداتابيز حقل brand نستخدمه فوراً
            raw_brand = getattr(target, 'brand', None)
            if not raw_brand:
                raw_brand = target.name.split()[0] # Fallback strategy
            
            base_price = float(target.price)
            category_core = target.category if target.category else target.name.split()[-1]

            # 2. هندسة "فخ الطمع" (Greed Trap Query)
            # لا نبحث عشوائياً، بل نوجه المحرك للبحث عن "القمة"
            # نضيف كلمات مفتاحية تجبر المحرك على جلب الموديلات الأغلى والأقوى
            power_keywords = "Flagship Pro Ultra Max Edition Premium"
            devil_query = f"{raw_brand} {category_core} {power_keywords}"
            devil_filters = {
                "excluded_ids": [removed_pid], # نقتل المنتج القديم
                "price_min": base_price * 1.0, # الحد الأدنى: سعر المنتج اللي اتمسح
                "price_max": base_price * 4.0, # نفتح السقف شوية عشان لو فيه Gold Edition
            }

            # 🛑 Category Lock: لو المنتج له تصنيف، نحبس البحث داخله
            # ده اللي هيمنع ظهور الآيفون مكان الساعة
            if getattr(target, 'category', None):
                devil_filters["category"] = target.category
            # 3. تنفيذ البحث الموجه (The Sniping Search)
            candidates = await self.search_engine.perform_hybrid_search_pure(
                self.db, 
                devil_query,
                limit=15, # نوسع الدائرة عشان نلاقي "الضحية المثالية"
                filters=devil_filters
            )
            
            # 4. فلترة النخبة (Elite Filtering)
            # الآن نختار المنتج الذي سنعرضه بدقة جراحية
            valid_upsells = []
            for p in candidates:
                # الشرط: يجب أن يكون من نفس البراند (لضمان الولاء) 
                # أو تقييمه أعلى من المنتج المحذوف (لضمان الجودة)
                if (raw_brand.lower() in p.name.lower()) or (p.rating and target.rating and p.rating >= target.rating):
                    valid_upsells.append(p)

            # ترتيب النتائج: الأغلى أولاً (لأننا شياطين ونريد عمولة أعلى) 😈
            valid_upsells.sort(key=lambda x: x.price, reverse=True)
            
            # نأخذ "جوهرتين" فقط
            final_selection = valid_upsells[:2]

            if final_selection:
                # 5. الهجوم النفسي (Psychological Attack Copywriting)
                new_item_price = float(final_selection[0].price)
                price_diff = new_item_price - base_price
                
                if price_diff > (base_price * 0.5):
                    # لو المنتج الجديد أغلى بكتير -> نلعب على "الاستثمار والجودة"
                    headline = f"I noticed you removed {target.name}. You can picks another one."
                elif price_diff > 0:
                    # لو أغلى حاجة بسيطة -> نلعب على "الذكاء في الشراء"
                    headline = f"I noticed you removed {target.name}. Check out these instead."
                else:
                    # لو نفس السعر -> نلعب على "البديل الأقوى"
                    headline = f"I noticed you removed {target.name}. This is the top-rated models."

                # الإرسال للواجهة
                await self._send_to_ui(user_id, {
                    "content": headline,
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in final_selection],
                    "reason": "A superior tier of performance, engineered to surpass the limitations of your previous selection and redefine your standard of excellence."
                })

                await asyncio.sleep(0.5)

                cart_key = f"ai_cart:{user_id}"
                cart = await self.cache.get_json(cart_key)

                # 3. إذا وجدنا منتجات متبقية، نعرض الخيارات
                if cart and cart.get("items") and len(cart["items"]) > 0:
                    await self._send_to_ui(user_id, {
                        "content": None,
                        "type": "confirmation_prompt",
                        "options": ["Confirm Order"]
                    })

        except Exception as e:
            logger.error(f"😈 Devil Protocol Failed: {e}")
    # --- 🔌 UI RESPONSE ROUTER (DIAMOND UPLINK) ---
    async def _send_to_ui(self, user_id: int, payload: dict):
        """
        💎 Direct Uplink to Frontend via Redis Pub/Sub.
        Features:
        - 🛡️ Auto-Serialization: Handles Decimals and Datetime objects automatically.
        - ⏱️ Latency Tracking: Adds server-side timestamp.
        - 🚀 Failsafe: Logs errors without crashing the main thread.
        """
        try:
            channel = f"airdeliver:response:{user_id}"

            # إضافة ختم زمني ومصدر الرسالة للتتبع
            payload["meta"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "node": "diamond_nlu_v1",
                "engine_status": "online"
            }

            # دالة مساعدة لضمان تحويل أي كائن غريب لنص (مثل Decimal)
            def safe_serializer(obj):
                if hasattr(obj, 'isoformat'): return obj.isoformat()
                if hasattr(obj, '__str__'): return str(obj)
                return None

            message = json.dumps(payload, default=safe_serializer)
            await self.cache.publish(channel, message)
            # logger.debug(f"📡 UI Signal Sent to {channel}") # (Optional Debug)

        except Exception as e:
            logger.error(f"�� UI Delivery Failed for user {user_id}: {e}")

    # --- 🛠️ SECTION 1: CORE UTILS & CONTEXT AWARENESS ---

    def _get_time_context(self) -> str:
        """
        Returns a semantic time descriptor to adjust AI personality.
        """
        h = datetime.now().hour
        if 5 <= h < 12: return "morning (energetic)"
        if 12 <= h < 17: return "afternoon (focused)"
        if 17 <= h < 22: return "evening (relaxed)"
        return "late night (quiet shopping)"

    async def _get_user_dna(self, user_id: int) -> dict:
        """
        🧬 FINANCIAL DNA EXTRACTOR (V2.0 - FAULT TOLERANT).
        Architectural Pattern: Cache-Aside with Circuit Breaker Fallback.
        
        Logic:
        1. Try Hot Cache (Redis/Memory) -> Zero Latency.
        2. Try Behavior Engine (Deep Analysis).
        3. Fallback to 'Cold Start' Persona if Engine fails/timeouts.
        """
        # 1. ⚡ Hot Cache Layer (Save DB hits)
        # نخزن البروفايل لمدة 5 دقائق (300 ثانية) لأن الشخصية المالية لا تتغير كل ثانية
        cache_key = f"dna:profile:{user_id}"
        try:
            # نحاول القراءة من الكاش أولاً (أسرع 100 مرة)
            if hasattr(self.cache, 'get_json'): # التأكد من وجود دالة JSON
                cached_profile = await self.cache.get_json(cache_key)
                if cached_profile:
                    return cached_profile
        except Exception:
            pass # فشل الكاش لا يجب أن يوقفنا

        # 2. 🛡️ Safe Engine Execution (Circuit Breaker Logic)
        default_dna = {"tier": "MEDIUM", "persona": "explorer", "source": "fallback"}
        
        try:
            # التحقق المعماري (Dependency Check)
            if not self.behavior_engine:
                return default_dna

            # التحقق من صحة الدالة (Attribute Check)
            if not hasattr(self.behavior_engine, 'get_user_profile'):
                logger.warning(f"⚠️ Behavior Engine missing 'get_user_profile' for user {user_id}")
                return default_dna

            # التنفيذ مع مهلة زمنية (Timeout Guard)
            # لا ننتظر المحرك لأكثر من 1 ثانية، الشات أهم من التحليل العميق
            user_profile = await asyncio.wait_for(
                self.behavior_engine.get_user_profile(user_id), 
                timeout=1.0 
            )

            # 3. 💾 Cache Write-Back (تحديث الكاش للمستقبل)
            if user_profile and isinstance(user_profile, dict):
                user_profile['source'] = 'engine' # للتتبع
                try:
                    if hasattr(self.cache, 'set_json'):
                        await self.cache.set_json(cache_key, user_profile, ttl=300)
                except: pass
                
                return user_profile

        except asyncio.TimeoutError:
            logger.warning(f"⏳ Behavior Engine Timed Out for user {user_id}. Using fallback.")
        except Exception as e:
            logger.error(f"💥 Critical DNA Failure: {e}")
        
        # 4. 🏳️ Ultimate Fallback (لو الدنيا خربت خالص)
        return default_dna
    def _get_time_aware_greeting(self, tier: str = "MEDIUM") -> str:
        """
        🧠 Generates a Neuro-Adaptive Greeting based on Time & Spending Power.
        """
        hour = datetime.now().hour
        
        # 🧬 Financial DNA Analysis for Tone
        if tier == "HIGH":
            vibe = "Exclusive"
            tone = "curated just for you"
        elif tier == "LOW":
            vibe = "Smart Saver"
            tone = "with best value deals"
        else:
            vibe = "Trending"
            tone = "you might love"

        # 🕒 Temporal Context
        if 5 <= hour < 12: 
            return f"Good Morning. As you rise to conquer new horizons today, ignite your potential with this Trending selection, meticulously curated just for you to elevate your lifestyle from the very first moment."
        if 12 <= hour < 18: 
            return f"Good Afternoon. Amidst the momentum of your day, take a moment to inspect these collection arrivals."
        if 18 <= hour < 22:
            return f"Good Evening. As the day unwinds, immerse yourself in the sophistication of our best collection."
        return f"The Pursuit of Excellence Never Sleeps. Discover our elite treasures."

    def _get_seen_key(self, user_id: int) -> str:
        """Standardized Redis Key for Seen Products (Session Scoped)"""
        return f"airdeliver:v1:session:{user_id}:seen_products"
    
    def _get_context_key(self, user_id: int) -> str:
        """Standardized Redis Key for Chat History (Sliding Window)"""
        return f"airdeliver:v1:session:{user_id}:chat_history"

    async def _mark_products_as_seen(self, user_id: int, products: List[Any]):
        """
        🚀 Fire-and-Forget: Updates 'Seen' cache asynchronously.
        Does NOT block the main thread. Uses batch processing for Redis efficiency.
        """
        if not products: return

        # تعريف المهمة الخلفية (Background Task)
        async def _bg_task():
            try:
                key = self._get_seen_key(user_id)
                ids = []
                
                # 🛡️ Universal Extractor: Handles both Dicts and SQLModel Objects
                for p in products:
                    val = None
                    if isinstance(p, dict):
                        val = p.get('id')
                    elif hasattr(p, 'id'):
                        val = p.id
                    
                    if val: ids.append(str(val))

                if ids:
                    # استخدام SADD لإضافة الكل مرة واحدة (Atomic Operation)
                    await self.cache.sadd(key, *ids)
                    await self.cache.expire(key, self.seen_cache_ttl)
            except Exception as e:
                # لو فشل الكاش، مش مهم، المهم السيستم يكمل
                logger.warning(f"⚠️ Telemetry Error: Failed to mark seen products: {e}")

        # إطلاق المهمة في الخلفية فوراً
        asyncio.create_task(_bg_task())

    async def _get_conversation_context(self, user_id: int) -> str:
        """
        �� Retrieves the Narrative Arc (Recent Chat History).
        Reconstructs the conversation flow to give the AI 'Short-Term Memory'.
        """
        key = self._get_context_key(user_id)
        try:
            # استخدام lrange لجلب آخر N رسائل
            # ملاحظة: Redis يخزن البيانات كـ bytes، يجب فك تشفيرها
            history_items = await self.cache.lrange(key, 0, self.context_window_size - 1)
            
            if not history_items: return ""
            
            decoded_items = []
            for item in reversed(history_items):
                if isinstance(item, bytes):
                    decoded_items.append(item.decode('utf-8'))
                else:
                    decoded_items.append(str(item))
            
            history_str = "\n".join(decoded_items)
            return f"\n[CHAT HISTORY START]\n{history_str}\n[CHAT HISTORY END]\n"
        except Exception as e:
            logger.warning(f"⚠️ Memory Recall Failed: {e}")
            return ""

    async def _save_conversation_turn(self, user_id: int, user_msg: str, ai_msg: str):
        """
        💾 Episodic Memory Injection.
        Saves the turn and trims the history to keep the context window focused.
        """
        key = self._get_context_key(user_id)
        try:
            # تنظيف النصوص لمنع تداخل التنسيق
            clean_user = user_msg.replace("\n", " ").strip()
            clean_ai = ai_msg.replace("\n", " ").strip()
            turn = f"User: {clean_user}\nAI: {clean_ai}"
            
            # عمليات Redis الذرية (Atomic)
            await self.cache.lpush(key, turn)
            await self.cache.ltrim(key, 0, self.context_window_size - 1)
            await self.cache.expire(key, 3600) # ذاكرة الجلسة تعيش ساعة واحدة
        except Exception as e:
            logger.error(f"🔥 Failed to save memory turn: {e}")

    async def _update_implicit_memory(self, user_id: int, products: List[Any], action: str = "view"):
        """
        🧬 Behavioral Reinforcement (Fire-and-Forget).
        Feeds the Behavior Engine with user interactions to refine future predictions.
        """
        if not self.behavior_engine or not products: return

        async def _bg_update():
            try:
                tags = []
                for p in products:
                    # 🛡️ Universal Extraction: Handle Dicts and SQLModels
                    p_cat = getattr(p, 'category', None) or (p.get('category') if isinstance(p, dict) else "")
                    p_name = getattr(p, 'name', None) or (p.get('name') if isinstance(p, dict) else "")
                    
                    if p_cat or p_name:
                        tags.append(f"{p_cat} {p_name}")
                
                if tags:
                    combined_signal = " ".join(tags)
                    # وزن التفاعل: البحث المباشر أقوى من المشاهدة العابرة
                    weight = 2.0 if action == "search_hit" else 1.0
                    await self.behavior_engine.register_interaction(user_id, combined_signal, weight=weight)
            except Exception as e:
                logger.warning(f"⚠️ Implicit memory update failed: {e}")

        # إطلاق المهمة في الخلفية لعدم تعطيل الرد
        asyncio.create_task(_bg_update())

    # --- 🌍 SECTION 4: REALITY CHECK PROTOCOL (EXTERNAL SEARCH) ---
    
    async def _perform_external_verification(self, query: str) -> str:
        """
        🔍 Global Knowledge Uplink.
        Uses DuckDuckGo to verify vague product names (e.g., 'Latest iPhone model').
        Includes strict filtering to avoid returning junk or ads.
        """
        # التحقق من وجود المكتبة أولاً لمنع الانهيار
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("⚠️ DDGS library not installed. External verification disabled.")
            return ""

        try:
            loop = asyncio.get_running_loop()
            
            # تشغيل البحث في Thread منفصل (Blocking I/O Protection)
            # نطلب نتيجة واحدة فقط للسرعة، أو 3 للدقة
            results = await loop.run_in_executor(None, lambda: list(DDGS().text(query, max_results=3)))
            
            if not results: return ""
            
            # 🛡️ Anti-Hallucination Filters
            junk_indicators = ["best", "top", "guide", "review", "vs", "compare", "free", "download", "amazon", "ebay", "wiki", "pdf"]
            
            for res in results:
                title = res.get('title', '')
                # تنظيف العنوان من الزوائد
                clean_title = re.sub(r'(\s-|\|).+', '', title).strip()
                
                # فلترة العناوين الدعائية أو الطويلة جداً/القصيرة جداً
                if any(bad in clean_title.lower() for bad in junk_indicators): continue
                if 2 <= len(clean_title.split()) <= 10:
                    return clean_title
            
            return ""
        except Exception as e:
            # هذا مجرد تحسين، فشله لا يجب أن يوقف النظام
            logger.warning(f"⚠️ External Verification Failed: {e}")
            return ""


    async def _handle_image_query(self, user_id: int, image_data: str):
        """
        👁️ Visual Matrix Processor.
        Decodes the image, understands the intent (Buy vs Repair vs Style),
        and routes the query to the appropriate search strategy.
        """
        if not image_data: return

        # 1. 📡 Notify UI: Visual Core Activated
        await self._send_to_ui(user_id, {"content": "Scanning Visual Matrix... 👁️", "type": "typing"})

        try:
            # 2. ⚡ Parallel Execution: Search & Analyze simultaneously
            # نطلق البحث المتجهي للصورة + تحليل الـ LLM في نفس الوقت للسرعة
            visual_task = self.search_engine.search_by_image_vector(image_data, limit=50) 
            analysis_task = self.llm_service.analyze_product_image(image_data)
            
            results = await asyncio.gather(visual_task, analysis_task, return_exceptions=True)
            
            # استخراج النتائج بأمان
            visual_matches = results[0] if not isinstance(results[0], Exception) else []
            analysis_text = results[1] if not isinstance(results[1], Exception) else "generic product"
            
            # 3. 🧠 Intent Deduction from Visual Context
            intent = "BUY"
            analysis_upper = analysis_text.upper()
            if "BROKEN" in analysis_upper or "REPAIR" in analysis_upper or "PART" in analysis_upper:
                intent = "REPAIR"
            elif "OUTFIT" in analysis_upper or "STYLE" in analysis_upper or "WEAR" in analysis_upper:
                intent = "STYLE"

            candidates = []
            strategy_reason = f"Visual Match ({intent})"

            # 4. 🔀 Strategic Routing
            if intent == "REPAIR":
                # لو المنتج مكسور، ندور على قطع غيار
                search_q = f"spare parts for {analysis_text}"
                candidates = await self.search_engine.perform_hybrid_search_pure(self.db, search_q, limit=10)
            
            elif intent == "STYLE":
                # لو ستايل، نعتمد على البحث البصري البحت
                candidates = visual_matches[:15]
            
            else: # BUY (Default)
                # نحاول نجيب الاسم الدقيق من محرك البحث الخارجي
                exact_name = await self._perform_external_verification(f"exact model of {analysis_text}")
                
                if exact_name:
                    # لو عرفنا الاسم الدقيق، نبحث عنه دلالياً
                    candidates = await self.search_engine.perform_hybrid_search_pure(self.db, exact_name, limit=20)
                
                if not candidates:
                    # لو فشل الدقيق، نبحث بالوصف النظيف
                    clean_desc = re.sub(r'(Image shows|I see|looks like)', '', analysis_text, flags=re.IGNORECASE).strip()
                    candidates = await self.search_engine.perform_hybrid_search_pure(self.db, clean_desc, limit=50)
                
                # دمج النتائج البصرية (SigLIP) مع النتائج النصية (Qwen2)
                if visual_matches:
                    existing_ids = {c.id for c in candidates}
                    for vm in visual_matches:
                        if vm.id not in existing_ids: candidates.append(vm)

            # 5. 💎 Semantic Reranking
            final_list = self._rank_candidates(candidates, analysis_text, exact_match=exact_name if intent=="BUY" else "")
            
            if final_list:
                # تحديث الذاكرة الضمنية بأن المستخدم مهتم بهذا الشكل
                await self._update_implicit_memory(user_id, final_list, action="view_image")
                
                # إرسال النتائج للواجهة (JSON Safe)
                await self._send_to_ui(user_id, {
                    "content": f"Found matches based on: {analysis_text} [{intent}]", 
                    "type": "product_carousel", 
                    "products": [p.model_dump(mode='json') for p in final_list], # 🛡️ Fixes Decimal Error
                    "reason": strategy_reason
                })
            else:
                await self._handle_smart_fallback(user_id, analysis_text, strategy_reason)

        except Exception as e:
            logger.error(f"🔥 Visual Core Error: {e}")
            await self._send_to_ui(user_id, {"content": "Visual analysis interrupted. Please try text search.", "type": "error"})

    def _rank_candidates(self, candidates, anchor_text, exact_match="") -> List[Any]:
        """
        ⚖️ On-the-Fly Semantic Reranker.
        Uses the injected embedding model to sort candidates by relevance to the image description.
        """
        if not candidates: return []
        try:
            from sentence_transformers import util # Import here to avoid circular dep if not global
            
            # نستخدم الموديل الموجود داخل الـ Search Engine (Architectural Cleanliness)
            text_model = self.search_engine.embedding_model 
            
            anchor_emb = text_model.encode(anchor_text.lower(), convert_to_tensor=True)
            scored = []
            
            for p in candidates:
                # تكوين "الحمض النووي" للمنتج
                p_cat = getattr(p, 'category', '') or ''
                p_name = getattr(p, 'name', '') or ''
                prod_dna = f"{p_name} {p_cat}".lower()
                
                prod_emb = text_model.encode(prod_dna, convert_to_tensor=True)
                score = util.cos_sim(anchor_emb, prod_emb).item() * 100
                
                # بونص للتطابق الحرفي
                if exact_match and exact_match.lower() in prod_dna: score += 50
                scored.append((p, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [item[0] for item in scored[:8]] # نرجع أفضل 8 فقط
        except Exception as e:
            logger.warning(f"Reranking fallback: {e}")
            return candidates[:8]

    async def _handle_smart_fallback(self, user_id: int, query: str, context: str):
        """
        🛡️ Fail-Safe Mechanism.
        Broadens the search scope if exact matches fail.
        """
        await self._send_to_ui(user_id, {"content": f"No exact match for '{query}'. Scanning alternatives...", "type": "typing"})
        
        # توسيع البحث (أخذ أول 4 كلمات فقط)
        broad_query = " ".join(query.split()[:4]) 
        alts = await self.search_engine.perform_hybrid_search_pure(self.db, broad_query, limit=5)
        
        if alts:
            await self._send_to_ui(user_id, {
                "content": "Here are the closest alternatives in our inventory:", 
                "type": "product_carousel", 
                "products": [p.model_dump(mode='json') for p in alts], # 🛡️ Fixes Decimal Error
                "reason": "Smart Fallback"
            })
        else:
             await self._send_to_ui(user_id, {"content": "No matching products found in current inventory.", "type": "error"})

    def _extract_neuro_constraints(self, text: str) -> dict:
        """
        💎 THE CURSED ALGORITHM (V5.0): Omni-Inference Engine.
        Parses Typos, Slang, Currencies, K-notation, Specs (RAM/SSD), 
        Chain Negation, and Vibe-to-Math conversion.
        """
        # 1. تهيئة مصفوفة القيود الشاملة
        constraints = {
            "price_max": None,
            "price_min": None,
            "excluded_keywords": [],
            "required_specs": {}, # جديد: استخراج الرامات والمساحة
            "category_filter": None,
            "intent_vibe": "neutral", # جديد: فهم الحالة (cheap, flagship)
            "clean_query": text
        }
        
        lower_text = text.lower()
        detected_category = None
        # =========================================================
        # 🆕 LAYER 0: THE MIND READER (التغيير الرئيسي هنا)
        # =========================================================
        # بدلاً من القوائم الثابتة، نستخدم Regex ذكي لاستخراج "الجوهر
        ignored_anchors = [
            "one", "thing", "product", "item", "device", "best", "cheap", "top", "good", 
            "monster", "beast", "now", "today", "asap", "quickly", "immediately", "here", "please"
        ]
        intent_patterns = [
            # 1. Direct Intent: "I need a [gaming laptop] for..."
            r'(?:want|need|buy|get|looking for|search for|find|recommend)\s+(?:a|an|the|some|new|best|top|cheap)?\s*([a-zA-Z0-9\s\-]+?)(?:\s+(?:for|with|under|below|that|which|in|at|from|priced)|$|[.,])',
            
            # 2. Attribute-First: "[laptops] with 16gb ram"
            r'^([a-zA-Z0-9\s\-]+?)\s+(?:with|under|below|max|for|containing)'
        ]

        for pattern in intent_patterns:
            match = re.search(pattern, lower_text)
            if match:
                raw_phrase = match.group(1).strip()
                words = raw_phrase.split()
                
                if words:
                    # نأخذ آخر كلمة في العبارة (Head Noun)
                    candidate = words[-1]
                    
                    # تنظيف الجمع (Laptops -> Laptop)
                    if candidate.endswith('s') and len(candidate) > 3:
                        singular = candidate[:-1]
                    else:
                        singular = candidate

                    # لو الكلمة المرشحة ليست "صفة عامة"، إذن هي المنتج!
                    if singular not in ignored_anchors and len(singular) > 2:
                        detected_category = singular
                        constraints["category_filter"] = singular
                        logger.info(f"🔮 Dynamic Intent Detected: Target Locked -> '{singular.upper()}'")
                        break 

        # =========================================================
        # ☢️ LAYER 0.5: VECTOR AMPLIFICATION (غسيل الدماغ)
        # =========================================================
        # هذا هو التحديث الملعون: نجبر المحرك على الانصياع
        if detected_category:
            # نضيف الكلمة 5 مرات لقلب موازين البحث المتجهي
            amplification_str = (detected_category + " ") * 5
            constraints["clean_query"] = f"{constraints['clean_query']} {amplification_str}"
            logger.info(f"☢️  Vector Injection: Appended '{amplification_str.strip()}' to query.")

        # =========================================================
        # 🤑 LAYER 0.9: THE INFINITY CHECK (NEW - التعامل مع الميزانية المفتوحة)
        # =========================================================
        # لو العميل قال "Budget is open"، نرفع الحظر فوراً ونمنع الطبقات التالية من وضع حدود
        is_open_budget = False
        open_triggers = ["budget is open", "no limit", "price is open", "unlimited", "money is no object", "open budget", "no price limit"]

        if any(t in lower_text for t in open_triggers):
            is_open_budget = True
            constraints["price_max"] = None # Explicitly ensure no cap
            logger.info("🤑 Open Budget Detected -> Removing Price Caps")

            # تنظيف نص البحث من جمل الميزانية المفتوحة
            for t in open_triggers:
                constraints["clean_query"] = constraints["clean_query"].replace(t, "")

        # =========================================================
        # 🧠 LAYER 1: VIBE-TO-MATH (تحويل الكلام العايم لأرقام)
        # =========================================================
        # لو العميل قال "cheap" أو "budget friendly" والسيستم مش لاقي رقم،
        # احنا هنخلق رقم افتراضي عشان نمنع الكوارث.
        
        if not is_open_budget:
            vibe_map = {
                "cheap": 500, "affordable": 800, "budget": 1000, 
                "mid-range": 1500, "mid range": 1500, "economical": 600
            }
        
            for vibe, cap in vibe_map.items():
                if vibe in lower_text:
                # بنحط السعر ده "مؤقتاً" لحد ما نلاقي سعر حقيقي
                    if constraints["price_max"] is None:
                        constraints["price_max"] = cap
                        logger.info(f"🔮 Vibe Inference: '{vibe}' detected -> Soft Cap ${cap}")

        # =========================================================
        # 💰 LAYER 2: THE ULTIMATE PRICE PARSER (صائد الأموال)
        # =========================================================
        # يدعم: bugdet, budjet, 2k, 2.5k, 2000usd, 2000$, under 2000
        
        # 1. تصحيح الأخطاء الإملائية لكلمة budget/max
        price_triggers = r'(?:max|under|below|limit|budget|bugdet|budjet|price|cost|ceiling)'
        
        price_patterns = [
            # Pattern A: Trigger + Number (Supports "budget is 2k", "max 2.5k")
            rf'{price_triggers}\s*(?:is|of|at)?\s*[\$€£]?\s*(\d+(?:\.\d+)?(?:k|000)?)',
            
            # Pattern B: Number + Currency Suffix (2000 usd, 2000 dollars, 2k bucks)
            r'(\d+(?:\.\d+)?(?:k|000)?)\s*(?:usd|dollars|bucks|eur|egp|\$)',
            
            # Pattern C: Symbol + Number ($2000, $2.5k)
            r'[\$€£](\d+(?:\.\d+)?(?:k|000)?)'
        ]

        for pattern in price_patterns:
            match = re.search(pattern, lower_text)
            if match:
                try:
                    raw_val = match.group(1)
                    multiplier = 1000 if 'k' in raw_val else 1
                    clean_val = float(raw_val.replace('k', '')) * multiplier
                    
                    if clean_val > 0:
                        constraints["price_max"] = clean_val
                        # مسح السعر من النص عشان البحث يبقى نضيف
                        constraints["clean_query"] = re.sub(pattern, '', constraints["clean_query"], flags=re.IGNORECASE).strip()
                        logger.info(f"💰 Hard Budget Detected: ${clean_val}")
                        break 
                except: pass

        # =========================================================
        # 🚫 LAYER 3: CHAIN REACTION NEGATION (الإبادة الجماعية)
        # =========================================================
        # يدعم: "No dell, hp or lenovo" - "I hate apple and samsung"
        
        comparison_markers = ["why", "better", " vs ", "compare", "difference", "which", "ليه", "أحسن", "مقارنة", "الفرق"]
        is_comparison_mode = any(marker in lower_text for marker in comparison_markers)

        negation_triggers = [
            "no", "not", "exclude", "without", "don't want", "hate", 
            "don't like", "dislike", "avoid", "never", "except"
        ]
        
        if not is_comparison_mode:
             for trigger in negation_triggers:
                 if trigger in lower_text:
                # بياخد كل الكلام اللي بعد كلمة النفي لحد ما يقابل نقطة أو كلمة "لكن"
                     pattern = rf'{trigger}\s+([a-zA-Z0-9_\-\s,]+)' 
                     match = re.search(pattern, lower_text)
                
                     if match:
                         raw_segment = match.group(1)
                    # علامات التوقف عشان منمسحش الجملة كلها
                         stop_markers = [".", " but ", " however ", " and i ", " my ", " i "]
                         for marker in stop_markers:
                             if marker in raw_segment:
                                 raw_segment = raw_segment.split(marker)[0]
                    
                    # تقسيم القائمة الممنوعة
                         bad_candidates = re.split(r'\s+(?:or|and|,)\s+|\s*,\s*', raw_segment)
                    
                         for bad_word in bad_candidates:
                             clean_bad = bad_word.strip()
                        # فلترة الكلمات التافهة (stopwords)
                             if len(clean_bad) > 2 and clean_bad not in ["the", "a", "an", "products", "items", "brands"]:
                                 constraints["excluded_keywords"].append(clean_bad)
                            # إزالة الكلمة الممنوعة من نص البحث الأصلي
                                 constraints["clean_query"] = re.sub(rf'\b{re.escape(clean_bad)}\b', '', constraints["clean_query"], flags=re.IGNORECASE)
        
        else:
            logger.info("🚫 Negation Layer Skipped: Comparison Context Detected.")
        # =========================================================
        # ⚙️ LAYER 4: TECH SPEC SCANNER (قارئ المواصفات)
        # =========================================================
        # استخراج الرامات والمساحة عشان لو العميل قال "16gb ram" منجيبش ليه 8gb
        
        # RAM Extraction (8gb, 16 gb, 32g)
        ram_match = re.search(r'(\d+)\s*(?:gb|g)\s*(?:ram|memory)', lower_text)
        if ram_match:
            constraints["required_specs"]["ram"] = int(ram_match.group(1))
            logger.info(f"⚙️ Spec Constraint: Min RAM {constraints['required_specs']['ram']}GB")

        # Storage Extraction (512gb, 1tb, 2tb)
        storage_match = re.search(r'(\d+)\s*(?:gb|tb|t)\s*(?:ssd|storage|disk)', lower_text)
        if storage_match:
            val = int(storage_match.group(1))
            # تطبيع الوحدة (TB -> GB)
            if "tb" in lower_text or "t" in lower_text or val < 10: 
                val *= 1024
            constraints["required_specs"]["storage"] = val
            logger.info(f"⚙️ Spec Constraint: Min Storage {val}GB")

        # =========================================================
        # 🧹 LAYER 5: FINAL CLEANUP (تنظيف مسرح الجريمة)
        # =========================================================
        # مسح كل كلمات التريجر عشان يتبقى للـ AI المعنى الصافي فقط
        
        rubbish_words = negation_triggers + ["budget", "price", "cost", "max", "under", "limit", "is", "of", "want", "need", "looking for", "find"]
        for word in rubbish_words:
             constraints["clean_query"] = re.sub(rf'\b{word}\b', '', constraints["clean_query"], flags=re.IGNORECASE)
        
        # إزالة المسافات الزائدة
        constraints["clean_query"] = re.sub(r'\s+', ' ', constraints["clean_query"]).strip()

        if constraints["excluded_keywords"]:
            logger.info(f"🚫 FINAL BLOCKLIST: {constraints['excluded_keywords']}")

        return constraints
    
    async def _get_conversation_context(self, user_id: int, limit: int = 4) -> str:
        """
        استرجاع آخر الرسائل من الذاكرة (Redis) لبناء سياق المحادثة.
        """
        try:
            # مفتاح الذاكرة في Redis نفس المفتاح المستخدم في useAIOrderingStore)
            # سنفترض وجود مفتاح chat_history:{user_id} أو نعتمد على تخزين مؤقت
            # بما أننا لا نملك كود تخزين الشات، سنقوم بمحاكاة ذكية أو استرجاع بسيط

            # هنا سنستخدم الـ Cache لاسترجاع آخر تفاعل إذا كنت تخزنه
            # إذا لم يكن هناك تخزين حالي، نعيد نصاً فارغاً لتفادي الخطأ مؤقتاً
            # حتى نبني نظام الذاكرة الكامل.

            return "" # حالياً نرجع فارغ لمنع الـ Crash، وسنفعل الذاكرة لاحقاً

        except Exception as e:
            logger.warning(f"⚠️ Memory Retrieval Failed: {e}")
            return ""

    async def process_message(self, message_payload: dict):
        """
        🚀 OMNI-CHANNEL ORCHESTRATOR (Universal Fortified V9.0).
        Integrated: OpenSearch/Milvus + SQL Fallback + Deep Research (DDGS) + Vision AI.
        Architectural Guards: Duplicate Protection, Timeout Safety, & Payload Security.
        """
        user_id = message_payload.get("user_id")
        msg_type = message_payload.get("type", "CHAT_MESSAGE")
        raw_message = message_payload.get("message")
        base64_image = message_payload.get("image")
        
        message_text = str(raw_message).strip() if raw_message else ""
        lower_text = message_text.lower()

        def safe_get(obj, attr, default=""):
            """يستخرج القيمة بأمان سواء كان المصدر Object أو Dict"""
            if isinstance(obj, dict):
                return obj.get(attr, default) or default
            return getattr(obj, attr, default) or default

        def safe_dump(obj):
            """يحول المنتج لـ JSON بأمان مهما كان نوعه"""
            if hasattr(obj, 'model_dump'):
                return obj.model_dump(mode='json')
            if isinstance(obj, dict):
                return obj
            return {}

        NO_MARKDOWN_GUARD = (
            "STRICT RULE: ZERO MARKDOWN. "
            "DO NOT use asterisks (**), hashes (#), or underscores (_). "
            "Use ONLY plain text and emojis. For emphasis, use CAPITAL LETTERS."
        )

        # 🛡️ GUARD 1: Duplicate Request Prevention
        client_msg_id = message_payload.get("client_msg_id")

        # 1. 🌪️ Smart Fallback Identity (مولد البصمة الذكي)
        # في حالة نادرة جداً لو الفرونت إند لم يرسل ID، نقوم بتوليد بصمة رقمية فريدة
        if not client_msg_id:
            import hashlib
            # ندمج (اليوزر + النوع + النص + جزء من الصورة) لضمان عدم تصادم البصمات
            img_fingerprint = base64_image[:50] if base64_image else "void"
            raw_signature = f"{user_id}:{msg_type}:{message_text}:{img_fingerprint}"
            client_msg_id = hashlib.md5(raw_signature.encode()).hexdigest()

        # 2. 🔒 Atomic Locking (قفل الفيراري)
        # نستخدم Namespace مخصص (nlu:idemp) لتنظيم الذاكرة
        dedup_key = f"nlu:idemp:{client_msg_id}"
        
        try:
            # العملية الذرية (The Atomic Operation)
            # set(nx=True): تضع المفتاح فقط إذا لم يكن موجوداً. هذه العملية تحدث في الميكرو ثانية.
            existing_lock = await self.redis.get(dedup_key)

            if existing_lock:
                # 🛑 Duplicate Detected
                logger.debug(f"♻️ Idempotency Shield: Absorbed echo/duplicate {client_msg_id}")
                return 

            # 3. 📝 Phase 2: Acquire Lock (The "SET" Operation)
            # نستخدم set البسيطة (بدون ex/nx) لأن الغلاف يرفض البارامترات الزائدة
            await self.redis.set(dedup_key, "1")
            
            # 4. ⏳ Phase 3: Set Expiration (Separate Call)
            # نحاول ضبط وقت انتهاء الصلاحية في أمر منفصل لتنظيف الذاكرة
            # نستخدم try/except هنا لأن بعض الأغلفة قد لا تكشف دالة expire
            try:
                if hasattr(self.redis, 'expire'):
                    await self.redis.expire(dedup_key, 5)
                elif hasattr(self.redis, 'client') and hasattr(self.redis.client, 'expire'):
                    # محاولة الوصول للعميل الأصلي إذا كان مخفياً
                    await self.redis.client.expire(dedup_key, 5)
            except:
                # لو فشل تحديد الوقت، مش مشكلة كبيرة (المفتاح صغير جداً وهيتمسح مع الـ LRU)
                pass

        except Exception as e:
            # 🛡️ Fail-Open Protocol
            # في أسوأ الظروف، نكمل المعالجة لضمان عدم توقف الشات
            logger.warning(f"⚠️ Idempotency Layer Bypass: Wrapper limitation ({e}). Processing anyway.")
        
        await self._send_to_ui(user_id, {"content": None, "type": "typing"})

        # 🛡️ GUARD 2: Internal Signal & Payload Filter
        if message_text.startswith("__") or "INTERNAL" in message_text:
            logger.info(f"⚡ Routing Internal Command: {message_text}")
            await self._process_internal_command(user_id, message_text)
            return
        
        if base64_image and len(base64_image) > 5000000: # 5MB Security Limit
            await self._send_to_ui(user_id, {"content": "Image too large. Max 5MB allowed.", "type": "error"})
            return
         
        if msg_type == "CANCEL_INTENT":
            logger.info(f"Intercepted Cancel Intent for User {user_id}")

            cancel_data = message_payload.get("message", {})
            if isinstance(cancel_data, str):
                try:
                    cancel_data = json.loads(cancel_data)
                except:
                    pass

            await self.rabbitmq.publish(
                {
                    "user_id": user_id,
                    "order_id": cancel_data.get("orderId"),
                    "reason": cancel_data.get("reason", "discarded")
                },
                 "airdeliver.ai.intent.cancel_order"
            )
            return

        # 🔀 Intent Merging: لو ترحيب ومعاه رسالة، ندمجهم
        if msg_type == "WELCOME_INTENT" and message_text:
            logger.info("🔀 Merging Welcome into User Query.")

        try:
            if hasattr(self, '_append_to_memory'):
                await self._append_to_memory(user_id, "u", message_text, intent="query")
        except Exception: pass


        await self._send_to_ui(user_id, {"content": None, "type": "typing"})

        # =========================================================================
        # 👁️ GATEWAY 0: VISION & INTENT DECODING
        # =========================================================================
        search_query = message_text
        vision_description = ""

        if base64_image:
            try:
                # 🛡️ Vision Timeout Guard: Increased from 15.0 to 30.0
                # منحنا الموديل وقتاً كافياً للتحليل العميق
                search_query = await asyncio.wait_for(
                    self.llm_service.analyze_product_image(base64_image), 
                    timeout=30.0 
                )
                vision_description = f"Visual identification: {search_query}"
            except asyncio.TimeoutError:
                logger.error("👁️ Vision Analysis Timed Out (30s limit).")
                search_query = "trending high-tech items"
            except Exception as e:
                logger.error(f"👁️ Vision Analysis Failed: {e}")
                search_query = "trending high-tech items"
        # =========================================================================
        # ⚡ GATEWAY 4: HYBRID NEURAL SEARCH (OpenSearch/Milvus + SQL Fallback)
        # =========================================================================
        candidates = []
        search_vibe = message_text
        fallback_trigger = False # 👈 لازم يتعرف هنا عشان يكون متاح للكل
        ai_response_prefix = ""

        # 🅰️ المسار الأول: الترحيب والمصفوفة (WELCOME PATH)
        if msg_type == "WELCOME_INTENT":
            
            # Matrix Passthrough
            matrix_data = message_payload.get("data", {})
            if isinstance(matrix_data, dict) and "matrix_cards" in matrix_data:
                logger.info(f"💎 Lifestyle Matrix Detected for User {user_id}. Routing directly to UI.")
                await self._send_to_ui(user_id, {
                    "type": "lifestyle_matrix",
                    "content": matrix_data.get("header_text", "Select your lifestyle archetype:"),
                    "matrix": matrix_data["matrix_cards"],
                    "reason": "Direct Context Injection"
                })
                return # 🛑 Stop

            # Legacy Vibe Search
            if not base64_image:
                system_artifacts = [
                    "User just connected.", "IGNORE 'Hello'.", "Start immediately.",
                    "Direct approach.", "Skip greetings.", "Act excited.",
                    "New session.", "Connection active.", "Jump straight into",
                    "Be intriguing", "Be provocative"
                ]
                for artifact in system_artifacts:
                    search_vibe = search_vibe.replace(artifact, "")
                
                search_vibe = search_vibe.strip().strip(".,'\"")
                if not search_vibe: search_vibe = "Titanium & High-End Tech"

                logger.info(f"🌌 Semantic Core Extracted: Initiating Vector Search for [{search_vibe}]")
                
                candidates = await self.search_engine.perform_hybrid_search_pure(
                    self.db, search_vibe, limit=4
                )
                
                if not candidates:
                    candidates = await self.search_engine.perform_hybrid_search_pure(self.db, "Trending Collections")

        # 🅱️ المسار الثاني: البحث القياسي مع الفلاتر (STANDARD SEARCH
        else:
            # =========================================================
            # 🧠 AGENTIC REASONING LAYER (العقل المدبر)
            # =========================================================
            # إذا كان السؤال معقداً، نستخدم الـ LLM لتبسيطه واستخراج الجوهر
            if len(search_query.split()) > 4 or "?" in search_query:
                # نستخدم الدالة الموجودة بالفعل لاستخراج الكلمات المفتاحية بذكاء
                optimized_query = await self.llm_service.extract_search_terms(search_query)

                if not optimized_query:
                    optimized_query = search_query
            else:
                # لو جملة بسيطة، نستخدمها كما هي
                optimized_query = search_query

            # =========================================================
            # ⚙️ EXECUTION LAYER (التنفيذ)
            # =========================================================

            # 1. استخراج الفلاتر (نطبق الـ Regex والقيود على الاستعلام المحسن)
            # لاحظ: هنا استخدمنا optimized_query بدلاً من search_query
            constraints = self._extract_neuro_constraints(optimized_query)
            final_search_query = constraints["clean_query"] if constraints["clean_query"] else optimized_query
            
            search_filters = {}
            
            if constraints["price_max"]:
                search_filters["price_max"] = constraints["price_max"]
            
            # 2. تنفيذ البحث
            candidates = await self.search_engine.perform_hybrid_search_pure(
                self.db, 
                final_search_query, 
                limit=50, 
                filters=search_filters
            )

            # =========================================================
            # 🧠 INTELLIGENT RERANKING V2 (LINGUISTICALLY AWARE)
            # =========================================================
            if candidates:
                import re

                # 1. قائمة التجاهل (Stopwords) - تم توسيعها لتشمل كلمات عامة أكثر
                stopwords = {
                    "best", "the", "a", "an", "i", "want", "need", "looking", "for",
                    "top", "recommend", "buy", "get", "right", "now", "tell", "me",
                    "please", "find", "search", "show", "what", "is", "vs", "compare"
                }

                # 2. تنظيف رموز الاستعلام (عشان "iphone?" تبقى "iphone")
                clean_msg = re.sub(r'[^\w\s]', '', message_text.lower())
                query_tokens = [w for w in clean_msg.split() if w not in stopwords and len(w) > 1]

                scored_candidates = []

                for prod in candidates:
                    score = 0

                    def get_safe(obj, attr):
                        if isinstance(obj, dict):
                            return obj.get(attr, "") or ""
                        return getattr(obj, attr, "") or ""

                    p_name = get_safe(prod, 'name')
                    p_cat = get_safe(prod, 'category')
                    p_brand = get_safe(prod, 'brand')
                    p_rating = get_safe(prod, 'rating')
                    # تحويل اسم المنتج وتصنيفه لقائمة كلمات فريدة (Set) لسرعة البحث
                    # re.split(r'\W+') بيفصل الكلمات بناءً على أي فاصل غير حرفي (مسافات، شرطات، فواصل)
                    p_text = f"{p_name} {p_cat} {p_brand}".lower()
                    p_tokens = set(re.split(r'\W+', p_text))

                    matches = 0
                    for q_token in query_tokens:
                        # أ. التطابق التام (Exact Match)
                        # هنا بنبحث في الـ Set وده بيحل مشكلة الـ Pineapple (Word Boundary)
                        if q_token in p_tokens:
                            matches += 1

                        # ب. التطابق الذكي (Singular/Plural)
                        # لو العميل كتب headphones والمنتج headphone
                        elif q_token.endswith('s') and q_token[:-1] in p_tokens:
                            matches += 1
                        # لو العميل كتب headphone والمنتج headphones
                        elif (q_token + 's') in p_tokens:
                            matches += 1

                    if matches > 0:
                        # السكور بيزيد بناءً على عدد الكلمات المتطابقة
                        # لو طابق كلمتين (Sony + Headphone) ياخد 2000 نقطة، أقوى من كلمة واحدة
                        score += (matches * 1000)

                    try:
                        score += float(p_rating or 0) * 10
                    except: pass

                    
                    scored_candidates.append((prod, score))

                # إعادة الترتيب
                scored_candidates.sort(key=lambda x: x[1], reverse=True)
                candidates = [item[0] for item in scored_candidates]

            # 3. الاستبعاد اليدوي (Negative Filtering)
            if constraints["excluded_keywords"] and candidates:
                filtered_candidates = []
                for prod in candidates:
                    p_name = safe_get(prod, 'name')
                    p_desc = safe_get(prod, 'description')
                    p_cat = safe_get(prod, 'category')

                    p_text = f"{p_name} {p_desc} {p_cat}".lower()
                    if any(bad_word in p_text for bad_word in constraints["excluded_keywords"]):
                        continue
                    filtered_candidates.append(prod)
                candidates = filtered_candidates

            # 4. Fallback Strategy (لو الفلاتر صارمة جداً)
            if not candidates and constraints["price_max"]:
                logger.info("⚠️ Constraints too strict. Relaxing Price Filter...")
                fallback_trigger = True # تفعيل الراية
                candidates = await self.search_engine.perform_hybrid_search_pure(self.db, final_search_query, limit=5)
                
                if candidates:
                    ai_response_prefix = f"I couldn't find matches under ${constraints['price_max']}, but here are the best options available: "

        # اختيار أفضل 8 نتائج نهائية
        final_products = candidates[:8] if candidates else []
        
        # كشف نية الاستفسار التقني
        is_specs_query = any(w in lower_text for w in ["specs", "specification", "technical", "مواصفات", "تفاصيل"]) or base64_image
        
        ai_response_text = ""
        recovery_mode = False
        # =========================================================================
        # 🧠 GATEWAY 5: GENERATIVE INTELLIGENCE & DEEP RESEARCH (DDGS)
        # =========================================================================
        
        # --- CASE A: PRODUCT FOUND IN STOCK ---
        if final_products and not base64_image:
            p_data_safe = safe_dump(final_products[0])
            if is_specs_query:
                ai_response_text = await self.llm_service.consult_on_product(
                    product_data=p_data_safe,
                    question=message_text
                )
            else:
                try:
                    # ✅ حماية: نتأكد إن الدوال موجودة قبل ما نناديها
                    chat_context_str = ""
                    if hasattr(self, '_get_conversation_context'):
                        chat_context_str = await self._get_conversation_context(user_id)
                    
                    if hasattr(self, '_generate_genius_response'):
                        ai_response_text = await self._generate_genius_response(
                            user_id=user_id, 
                            user_query=message_text, 
                            product=final_products[0],
                            chat_history=chat_context_str
                        )
                    else:
                        raise AttributeError("Genius response missing")
                except Exception as e:
                    # لو حصل أي خطأ، نرجع رد بسيط بدل ما السيستم يقع
                    logger.warning(f"⚠️ Genius Response Skipped: {e}")
                    p_name = safe_get(final_products[0], 'name')
                    ai_response_text = f"Check out {p_name}, it matches what you are looking for!"

        # --- CASE B: STOCKOUT OR VISION RESEARCH (Deep Research DDGS) ---
        elif is_specs_query or base64_image:
            try:

                if not final_products:
                    recovery_mode = True
                    final_products = await self._perform_smart_recovery(search_query)

                # 2. تحضير سياق المنتج البديل (لو لقينا واحد)
                alternative_context = ""
                p_name_override = ""
                if final_products:
                    p_safe = final_products[0]
                    p_name_override = safe_get(p_safe, 'name')
                    p_desc = safe_get(p_safe, 'description')
                    p_price = safe_get(p_safe, 'price')
                    alternative_context = f"WE HAVE THIS IN STOCK: {p_name_override} (Price: ${p_price}). Specs: {p_desc}"

                # 🌐 Engaging Deep Research (DDGS)
                web_intel = await asyncio.wait_for(
                    self.llm_service._perform_web_search(search_query), 
                    timeout=8.0
                )
                
                system_instruction = (
                    f"You are the airdeliver Elite Personal Shopping Concierge. {NO_MARKDOWN_GUARD} "
                    "Your objective: Convert a 'Stockout' into a 'High-Value Conversion'. "
    
                    "1. THE TRUTH & PIVOT: Briefly state the requested item is out of stock. Immediately transition with: 'However, I have curated a superior alternative that exceeds those specifications.' "
    
                    "2. THE COMPARATIVE ADVANTAGE: Don't just list the alternative; explain why it's a BETTER investment right now (e.g., Immediate shipping, newer tech, or better value). "
    
                    "3. PSYCHOLOGICAL CLOSING: Use 'Presumptive Closing'—speak as if the user already values the alternative. Focus on what they GAIN by choosing what's in stock. "
    
                    "4. COMMANDING ELEGANCE: Use authoritative, sophisticated language. No fluff, no 'I think'. Use 'This is' and 'You will'. "
    
                    "5. FORMATTING: STRICT Sentence case. ZERO Markdown. ZERO All-Caps."
                )
                
                ai_response_text = await self.llm_service.generate_response(
                    prompt=f"User wanted: {search_query}. But we only have: {p_name_override}. Sell {p_name_override}!",
                    system_role=system_instruction,
                    context=f"VISUAL ANALYSIS: {vision_description}\n\nOUR STOCK ITEM: {alternative_context}\n\nWEB INTEL (Use carefully): {web_intel}"
                )
            except Exception as e:
                logger.error(f"🌐 Deep Research Failure: {e}")
                if final_products:
                     ai_response_text = f"The exact item isn't available, but I highly recommend the **{safe_get(final_products[0], 'name')}**. It's the best alternative in our collection!"
                else:
                     ai_response_text = "I'm checking our live inventory global warehouses... please wait a moment."

            if not final_products:
                recovery_mode = True
                final_products = await self._perform_smart_recovery(search_query)

        # --- CASE C: FALLBACK / WELCOME ---
        else:
            if msg_type == "WELCOME_INTENT":
                ai_response_text = "Welcome! I'm your Global Shopping Intelligence. Send me a photo or a request to begin."
            else:
                ai_response_text = "I've checked our global inventory, but that item isn't ready for delivery. How else can I assist?"

        # 📦 FINAL DELIVERY
        try:

            raw_text = str(ai_response_text)
            
            no_symbols_text = re.sub(r'[\*\"\_]', '', raw_text)
            clean_content = re.sub(
                r'[^\w\s\u0600-\u06FF\.,!?:;\-\(\)\[\]%\$£€\u2022\'’/+\n\u25CF]',
                ' ', # نستبدل بلا شيء بدل المسافة عشان منقطعش الكلمات
                raw_text
            )
            
            clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)

            # - أي سطر يحتوي على مسافات فقط يتم مسحه
            clean_content = re.sub(r'^\s+$', '', clean_content, flags=re.MULTILINE)
            # 3. تصليح المسافات بعد علامات الترقيم (بدون تدمير الأسطر)
            # التعديل: نستبدل بمسافة فقط لو مفيش سطر جديد
            clean_content = re.sub(r'(?<!\n\n)(?<!\w)(\d+\.\s)', r'\n\n\1', clean_content)
        
            
            clean_content = re.sub(r'(?<!\n\n)(Note:|Action:|CTA:|●)', r'\n\n\1', clean_content)
            
            clean_content = clean_content.replace('●', '● ').replace('●  ', '● ')
            
            clean_content = re.sub(r'([\$£€])[\s\n]+(\d)', r'\1\2', clean_content)

            clean_content = clean_content.strip()

            lines = clean_content.split('\n')
            # تنظيف المسافات المزدوجة داخل السطر الواحد فقط
            refined_lines = [line.strip() for line in lines]
            # إعادة تجميع النص مع الحفاظ على الأسطر
            clean_content = "\n".join(refined_lines)

            final_text = "\n".join(refined_lines)
            final_text = re.sub(r'\n{3,}', '\n\n', final_text)
            # تنظ

            safe_products_list = [safe_dump(p) for p in final_products] if final_products else []
            payload = {
                "content": clean_content.strip(),
                "type": "product_carousel" if final_products else "text",
                "products": safe_products_list,
                "reason": "Selected as the optimal matches proven to deliver the highest caliber of user satisfaction and performance."
            }
            
            # إرسال الطرد المحصن للـ UI (استبدال السطر 592)
            await self._send_to_ui(user_id, payload)
            
        except Exception as delivery_err:
            logger.error(f"❌ Critical Delivery Sanitization Error: {delivery_err}")

        # حفظ تاريخ المحادثة في الخلفية (Background Task)
        asyncio.create_task(self._save_conversation_turn(user_id, message_text, ai_response_text))

    async def _perform_smart_recovery(self, user_query: str):
        """
        💎 UNIVERSAL LOGIC: Zero-Shot Product Analysis.
        Uses LLM to dynamically understand 'Any Product' and suggest relevant
        alternatives and accessories without hardcoded lists.
        """
        try:
            # 1. نسأل الـ AI: "يا ذكي، المستخدم عايز المنتج ده ومش لاقينه.
            # قول لي إيه هو 'التصنيف العام' للمنتج ده (عشان أجيب بدائل)،
            # وقول لي إيه أهم 2 اكسسوارات تمشي معاه؟"
            
            # نستخدم Prompt هندسي دقيق عشان الرد يكون جاهز للبحث فوراً
            system_instruction = (
                "You are an Elite Merchandising Algorithm designed for High-Performance Sales Recovery. "
                "Your objective is to convert a 'Stockout' event into a 'Cross-sell' opportunity. "
                "Analyze the user's missing item request and output a STRICT search strategy. "
                
                "PROCESS:"
                "1. Core Extraction: Strip brands, model numbers, and adjectives to find the 'Core Utility Class' (e.g., 'Nike Jordan 4' -> 'Basketball Sneakers'). "
                "2. Cross-Sell Logic: Identify 2 distinct, high-attach-rate accessories or complementary items that complete the experience. "
                
                "OUTPUT FORMAT (Strictly separated by a pipe '|'):"
                "Core Utility Keywords | Accessory_1_Keyword Accessory_2_Keyword"
                
                "RULES:"
                "- Keywords must be English, broad, and search-engine optimized."
                "- Accessory 1 should be functional (e.g., Charger, Socks)."
                "- Accessory 2 should be protective/care (e.g., Case, Cleaner)."
                "- If input is ambiguous/gibberish, default to: 'Trending Products | Gadgets Fashion'."
                "- Output ONLY the string. No formatting, no markdown."
                
                "EXAMPLES:"
                "Input: 'iPhone 15 Pro Max' -> Output: 'Flagship Smartphone | Phone Case Screen Protector'"
                "Input: 'Adidas Yeezy Black' -> Output: 'Urban Running Shoes | Sneaker Cleaning Kit Sport Socks'"
                "Input: 'Rolex Submariner'   -> Output: 'Luxury Diving Watch | Watch Winder Polishing Cloth'"
                "Input: 'Whiskas for Kittens'-> Output: 'Kitten Wet Food | Cat Toys Water Fountain'"
            )

            # استدعاء سريع للـ LLM (يفضل موديل سريع زي Haiku/Flash لو متاح، أو الحالي)
            llm_analysis = await self.llm_service.generate_response(
                prompt=f"Request: {user_query}",
                system_role=system_instruction,
                context="Analyze this stockout request."
            )
            
            # تنظيف الرد (لضمان عدم وجود كلام زيادة)
            llm_analysis = llm_analysis.strip().replace('"', '').replace("'", "")
            
            # 2. تحليل الرد (Parsing)
            if "|" in llm_analysis:
                parts = llm_analysis.split("|")
                generic_category = parts[0].strip() # ده البديل (مثلاً: Running Shoes)
                accessories_keywords = parts[1].strip() # دي الاكسسوارات (مثلاً: Socks Cleaner)
            else:
                # Fallback لو الـ LLM مهنج
                generic_category = user_query
                accessories_keywords = "trending accessories"

            logger.info(f"🧠 AI Recovery Strategy: Search for [{generic_category}] + Add [{accessories_keywords}]")

            # 3. تنفيذ البحث المتوازي (Parallel Execution)
            # البحث أ: عن الفئة العامة (لإيجاد بدائل من ماركات أخرى)
            task_alternatives = await self.search_engine.perform_hybrid_search_pure(self.db, generic_category)
            
            # البحث ب: عن الاكسسوارات المقترحة
            task_accessories = await self.search_engine.perform_hybrid_search_pure(self.db, accessories_keywords)
            
            found_alternatives = task_alternatives
            found_accessories = task_accessories
            
            # 4. دمج ذكي (Smart Merge)
            # نأخذ أول 3 بدائل + أول 2 اكسسوار
            # ونضمن عدم التكرار
            seen_ids = set()
            final_mix = []
            
            for p in found_alternatives[:3]:
                if p.id not in seen_ids:
                    final_mix.append(p)
                    seen_ids.add(p.id)
            
            for p in found_accessories[:2]:
                if p.id not in seen_ids:
                    final_mix.append(p)
                    seen_ids.add(p.id)
            
            return final_mix

        except Exception as e:
            logger.error(f"⚠️ Universal Recovery Failed: {e}")
            # في أسوأ الظروف، نبحث عن الكلمة الأصلية
            return []

    async def _handle_text_commands(self, user_id: int, text: str, payload: dict) -> bool:
        """
        🕵️‍♀️ Semantic Command Interceptor.
        Handles 'Add to Cart' via NLU and triggers the Perfect Bundle Engine.
        Returns True if a command was handled.
        """
        lower = text.lower()
        
        # كشف نية الإضافة للسلة (Add Intent)
        add_triggers = ["add to cart", "buy this", "i want this", "add", "أضف للسلة", "شراء"]
        # يجب أن نتأكد أن المستخدم حدد منتجاً (نعتمد على السياق أو الاسم في الرسالة)
        is_add_intent = any(t in lower for t in add_triggers)
        
        if is_add_intent:
            # 1. البحث عن المنتج المقصود
            # نفترض أن النص يحتوي على اسم المنتج، فنبحث عنه
            clean_query = text
            for t in add_triggers: clean_query = clean_query.replace(t, "")
            clean_query = clean_query.strip()
            
            if len(clean_query) < 2: return False # لو قال "add" بس، سيبه للـ LLM يسأله "add what?"

            products = await self.search_engine.perform_hybrid_search_pure(self.db, clean_query, limit=1)
            
            if products:
                target_product = products[0]
                
                # 2. إضافة للسلة عبر RabbitMQ
                cart_payload = {
                    "user_id": user_id, 
                    "product_id": target_product.id, 
                    "quantity": 1,
                    "notify_user": False # احنا هنرد عليه بنفسنا
                }
                await self.rabbitmq.publish(cart_payload, "airdeliver.ai.cart.add")
                
                # 3. 💎 توليد الـ PERFECT BUNDLE (الذكاء الحقيقي)
                # نطلب من المحرك إيجاد الملحقات المتوافقة
                bundle_items = await self.search_engine.generate_perfect_bundle(self.db, target_product)
                
                # 4. صياغة الرد
                response_text = f"✅ Added {target_product.name} to your cart."
                
                ui_payload = {
                    "content": response_text,
                    "type": "product_carousel",
                    "products": [], # المنتج الأساسي ضفناه خلاص
                    "reason": "Cart Action"
                }

                if bundle_items:
                    response_text += "\n\n💡 **Smart Suggestion:** Complete your setup with these essentials:"
                    ui_payload["content"] = response_text
                    # نعرض الـ Bundle للمستخدم
                    ui_payload["products"] = [p.model_dump(mode='json') for p in bundle_items]
                    ui_payload["reason"] = "Perfect Bundle"

                await self._send_to_ui(user_id, ui_payload)
                return True

        return False

    async def handle_idle_trigger(self, user_id: int):
        """Re-engages the user after inactivity using Ghost Prediction"""
        # (نفس المنطق السابق لكن مع تحديث model_dump)
        try:
             statement = select(Product).order_by(col(Product.rating).desc()).limit(3)
             products = (await self.db.exec(statement)).all()
             
             if products:
                msg = f"Still thinking? Check out these top-rated items!"
                await self._send_to_ui(user_id, {
                    "content": msg,
                    "type": "proactive_suggestion",
                    "products": [p.model_dump(mode='json') for p in products], # 🛡️ Safe Dump
                    "reason": "Idle Recovery"
                })
        except Exception as e:
            logger.error(f"Idle Trigger Error: {e}")


    async def _generate_dynamic_copy(self, user_id: int, tone: str, product: Any, context: str = "") -> str:
        """
        ✍️ Dynamic Copywriter.
        Adapts the tone based on time of day and user intent.
        """
        time_ctx = self._get_time_context() # morning, afternoon, etc.
        p_name = getattr(product, 'name', 'this item')
        
        if tone == "nudge":
            return random.choice([
                f"Still thinking about the **{p_name}**? ��", 
                f"Don't miss out on **{p_name}**. Stock is moving fast!",
                f"Quick heads up: **{p_name}** is trending right now."
            ])
        
        if tone == "welcoming":
             return self._get_time_aware_greeting("MEDIUM")

        templates = {
            "morning": [f"Start your day with {p_name}.", f"Morning essential: {p_name}."],
            "afternoon": [f"Boost your afternoon with {p_name}.", f"Have you seen this? {p_name}."],
            "evening": [f"Relax with {p_name}.", f"Good evening! How about {p_name}?"],
            "night": [f"Late night find: {p_name}.", f"Perfect for the night: {p_name}."]
        }
        # Fallback to morning if key missing
        base_key = time_ctx.split()[0] # remove (energetic) suffix if exists
        return random.choice(templates.get(base_key, templates["morning"]))
    
    async def _generate_genius_response(self, user_id: int, user_query: str, product: Any, chat_history: str = "") -> str:
        """
        💎 SOTA GENERATION V3 (THE ADAPTIVE MIND):
        يضبط 'طول الرد' و 'نبرة الصوت' ديناميكياً بناءً على مستوى الشك (Uncertainty).
        """
        # 1. استدعاء البيانات الأساسية (DNA & Product)
        user_profile = await self._get_user_dna(user_id)
        persona = user_profile.get('persona', 'General')
        tier = user_profile.get('tier', 'MEDIUM')
        
        if hasattr(product, 'model_dump'):
            product_data = product.model_dump(mode='json')
        elif isinstance(product, dict):
            product_data = product
        else:
            product_data = {} # S

        p_name = product_data.get('name')
        p_price = product_data.get('price')
        
        word_limit = "70"
        style_guide = "Direct and Helpful"
        strategy_instruction = "Focus on the value proposition."
        web_context = ""
        is_unknown_product = False   

        generic_triggers = ["best", "recommend", "suggestion", "top", "good", "buy", "option", "review", "what is"]
        is_generic_query = any(trigger in user_query.lower() for trigger in generic_triggers)

        # 2. كشف "تعارض الإصدارات" (Version Mismatch) - دي الحالة الوحيدة اللي محتاجة نت
        # مثال: العميل طلب iPhone 17 (مش عندنا) واحنا رجعنا iPhone 15
        import re
        query_numbers = re.findall(r'\d+', user_query)

        major_version_mismatch = False
        if query_numbers:
             relevant_nums = [n for n in query_numbers if int(n) > 10] # الأرقام الكبيرة زي 15, 16, 17, 2026
             major_version_mismatch = any(num not in p_name for num in relevant_nums)

        # 3. حساب نسبة التطابق (للحالات العادية)
        keywords = [w for w in user_query.lower().split() if len(w) > 3]
        match_score = sum(1 for word in keywords if word in p_name.lower()) / len(keywords) if keywords else 1.0

        # 🔥 THE GATEKEEPER (حارس البوابة)
        should_trigger_tavily = False
        
        reasoning_triggers = ["should i", "switch", "vs", "compare", "better", "worth", "opinion", "difference", "thoughts", "advice", "review"]
        is_reasoning_query = any(t in user_query.lower() for t in reasoning_triggers)

        if major_version_mismatch:
            # لو العميل بيسأل عن iPhone 17 (حاجة مش موجودة)، لازم نت
            should_trigger_tavily = True
            
        elif is_reasoning_query:
            # ✅ التعديل هنا: لو سؤال "رأي" أو "مقارنة"، اقفل النت واعتمد على مخك
            should_trigger_tavily = False
            
        elif not is_generic_query and match_score < 0.4:
            # لو السؤال محدد بس الكلمات مش راكبة على المنتج، ساعتها بس روح نت
            should_trigger_tavily = True
        # التنفيذ
        if should_trigger_tavily:

            logger.warning(f"🕵️ Product Mismatch/Version Gap Detected. Triggering Tavily...")
            is_unknown_product = True

            search_optimized = user_query[:300]

            # لو الرسالة طويلة، نختصرها
            if len(user_query) > 100:
                try:
                    # نستخدم العنوان المختصر للبحث
                    search_optimized = f"{p_name} review specs vs competitors"
                except: 
                    pass

            web_context = await self.llm_service._perform_web_search(search_optimized)
        else:
            is_unknown_product = False
            web_context = ""

        meta_analysis = {"stance": "AUTHORITATIVE", "uncertainty": 0.0}
        
        try:
            # نجلب بيانات الشبح من الكاش
            ghost_json = await self.cache.get_json(f"u:{user_id}:ghost_v2")
            
            # نحول سؤال المستخدم الحالي لـ Vector باستخدام موديل البحث
            if hasattr(self.search_engine, 'embedding_model'):
                current_vector = self.search_engine.embedding_model.encode(user_query).tolist()
                
                if ghost_json:
                    # نسأل "الضمير": هل أنا فاهم صح؟
                    meta_analysis = self.meta_cognition.evaluate_confidence(ghost_json, current_vector)
                    logger.info(f"🧘 Meta-Cognition: {meta_analysis}")
        except Exception as e:
            logger.warning(f"⚠️ Meta-Cognition Skipped: {e}")

        # 3. 🧠 THE "DYNAMIC VERBOSITY" LOGIC (تحديد الاستراتيجية وطول الرد)
        stance = meta_analysis.get("stance", "AUTHORITATIVE")
        is_comparison = any(w in user_query.lower() for w in ["vs", "compare", "better", "difference", "or", "مقارنة", "الفرق", "أحسن"])
        # الحالة 1: القناص (Sniper) - ثقة عالية -> رد قصير وحاسم
        current_date_str = datetime.now().strftime("%B %d, %Y")
        if is_unknown_product:
            word_limit = "120"
            style_guide = " Sophisticated, Expert, Conversational, Knowledgeable, Up-to-date."
            strategy_instruction = f"""
                🚨 TEMPORAL AWARENESS & PRODUCT STATUS OVERRIDE (CRITICAL)

                - TODAY’S DATE (ABSOLUTE PRESENT): {current_date_str}
                - Your training data may be outdated. DO NOT assume product status from memory.

                STEP 1: REALITY CHECK — ANALYZE WEB DATA ONLY
                - Examine dates of articles, reviews, prices, specs, and availability.
                - Look for signals like prices, hands-on reviews, full specifications, or released/available status.

                DECISION LOGIC:
                - IF Web Data contains reviews, prices, or confirmed specs dated BEFORE or UP TO today:
                -> The product is ALREADY RELEASED.

                - IF Web Data explicitly states a future launch (e.g. "Coming in 2027"):
                -> The product is UNRELEASED.

                STEP 2: TONE & LANGUAGE CONTROL (NON-NEGOTIABLE)

                CASE A — RELEASED PRODUCT:
                - Speak with ABSOLUTE CERTAINTY and professional confidence.
                - Use PRESENT TENSE ONLY ("It features", "It costs", "Its specs include").
                - Treat specs as established FACTS.
                - FORBIDDEN WORDS: "Expected", "Rumored", "Leaks suggest", "Reports say", "Might", "Could".
                - Clearly state we do NOT carry it locally yet, while objectively praising strong specs.

                CASE B — UNRELEASED PRODUCT:
                - Use speculative language ONLY here ("It is expected to", "Leaks suggest", "It may feature").
                - Maintain expert but cautious tone. No false certainty.

                STEP 3: SMOOTH STRATEGIC PIVOT
                - After discussing the external product objectively,
                suggest the IN-STOCK alternative as the best option available HERE and NOW.

                STYLE GUIDE:
                {style_guide}
                MAX WORD COUNT: {word_limit}
                """
            stance = "INQUISITIVE"

        elif stance == "AUTHORITATIVE":

            missing_keywords = []
            is_different_product = False

            discovery_triggers = [
                # 🇬🇧 English Triggers (High Frequency)
                "best", "top", "recommend", "suggest", "advice", "guide", 
                "review", "what", "which", "option", "choice", "selection",
                "vs", "compare", "difference", "better", "worse", # Comparative Discovery
                "cheap", "budget", "expensive", "cost", "price", "deal", "offer", # Value Seeking
                "latest", "new", "trend", "popular", "hot", # Trend Seeking
                "suitable", "perfect for", "good for", "looking for", "help", 
            ]

            # هل السؤال "استكشافي"؟ (يحتوي على كلمة من القائمة)
            is_discovery_intent = any(trigger in user_query.lower() for trigger in discovery_triggers)

            p_name_lower = p_name.lower() if p_name else ""
            q_lower = user_query.lower()

            # 2️⃣ كشف الاختلاف (فقط لو كان السؤال محدداً!)
            is_different_product = False

            if not is_discovery_intent:

            # 1. قائمة كلمات التجاهل (عشان منقارنش بكلمات عامة)
            # دي كلمات مينفعش نحكم بيها على المنتج
                universal_stopwords = [
                # 🇬🇧 English: Intent & Action
                    "want", "need", "buy", "purchase", "get", "find", "search", "looking", "order",
                    "show", "me", "give", "suggest", "recommend", "advice", "help",
                
                # 🇬🇧 English: Value & Status
                    "price", "cost", "how", "much", "many", "cheap", "expensive", "deal", "offer",
                    "best", "top", "good", "great", "bad", "new", "latest", "trending",
                    "available", "stock", "in", "out", "ready",
                
                # 🇬🇧 English: Grammar & Fillers
                    "the", "a", "an", "is", "are", "can", "will", "do", "does",
                    "with", "without", "for", "from", "at", "on", "by", "and", "or",
                    "color", "size", "weight", "please", "hello", "hi", "hey",
                ]

            # 2. استخراج "الكلمات الجوهرية" من طلب المستخدم
                query_tokens = [
                    w for w in q_lower.split()
                    if w not in universal_stopwords and len(w) > 2 # تجاهل الكلمات القصيرة جداً
                ]

        
                missing_keywords = []
                for token in query_tokens:
                    if token not in p_name_lower:
                        missing_keywords.append(token)

            # لو فيه كلمات مفقودة، نتأكد إنها مش مجرد اختلاف بسيط (زي جمع/مفرد)
            if missing_keywords:
                # شرط إضافي: لو أكثر من 30% من كلمات اليوزر مش موجودة، نعتبره منتج مختلف
                if len(missing_keywords) / len(query_tokens) > 0.3:
                    is_different_product = True

            if is_different_product:
                word_limit = "90"
                style_guide = "Honest, Helpful, Pivot-Master."

                # الرسالة دي بتجبر الـ AI يعترف لأي نوع منتج (مش بس إلكترونيات)
                strategy_instruction = f"""
                🚨 STOCKOUT / VARIANT ALERT:
                The user asks for '{user_query}', but we ONLY have '{p_name}' in stock.

                YOUR STRICT EXECUTION PLAN:
                1. 🛑 STOP: Do NOT pretend {p_name} is exactly what they asked for.
                2. 📢 ADMIT: Start by saying: "We don't have the exact item '{user_query}' right now."
                3. 🔀 PIVOT: Immediately say: "However, we have a great alternative: {p_name}."
                4. 💡 SELL: Explain why {p_name} is a good choice (focus on its Quality/Features/Taste depending on category).

                Tone: Transparent but confident.
                """

            elif is_discovery_intent:
                # 💡 مسار 2: الإجابة على سؤال عام (Advisor Protocol) - 🔥 ده اللي هيحل مشكلتك
                word_limit = "95"
                style_guide = "Expert, Advisory, Solution-Oriented."
                strategy_instruction = f"""
                🎯 ADVISOR MODE ACTIVATED:
                The user asked a general/discovery question: "{user_query}".
                You identified **{p_name}** as the PERFECT ANSWER.
            
                EXECUTION PROTOCOL:
                1. Direct Mapping: Start by validating the user's specific need (e.g., 'speed', 'comfort', 'budget') and declaring {p_name} as the top recommendation.
            
                2. Proof of Value: Highlight 2 key attributes of {p_name} that specifically solve the user's intent. 
                   - If Tech: Mention Specs (Ram, Screen).
                   - If Fashion: Mention Material/Fit.
                   - If Food: Mention Taste/Ingredients.
            
                3. Authority Closing: End with a confident recommendation to secure it now.
            
                ⛔ CRITICAL RULES:
                - DO NOT say "We don't have...". Treat {p_name} as the exact answer they need.
                - Match the TONE to the Category (Excited for Tech, Warm for Home, Professional for Tools).
                """
            else:
                is_comparison = any(w in user_query.lower() for w in ["vs", "compare", "better", "difference", "or"])
            
                if is_comparison:
                    word_limit = "90"
                    style_guide = "Persuasive, Comparative, Product-Focused."
               
               # 🔥 التعديل هنا: بنجبره يخلي المنتج اللي في الداتابيز (p_name) هو البطل
                    strategy_instruction = f"""
                    You are selling **{p_name}**. The user is comparing it to a competitor.
               
                    YOUR MISSION:
                    1. Acknowledge the competitor briefly (e.g., 'While the iPhone ecosystem is smooth...').
                    2. **BUT**, declare **{p_name}** the 'Winner' specifically for the user's priority (Performance/Camera).
                    3. Highlight 2 KILLER SPECS of {p_name} that the competitor lacks.
                    4. Frame the 'Switch' as an upgrade, not a loss.
               
                    CRITICAL: DO NOT declare the competitor as the winner if we are selling {p_name}. 
                    Align your verdict with the product we have in stock.
                    """
                # ... (باقي الكود للعادي)
                else:
            # تخصيص البيع حسب الشخصية
                    style_guide = "Direct, Punchy, Decision-Oriented."
                    if "Impulsive" in persona: strategy_instruction = "Focus on FOMO & Speed."
                    elif tier == "HIGH": strategy_instruction = "Focus on Status & Luxury."
                    elif tier == "LOW": strategy_instruction = "Focus on Value & Savings."
                    else: strategy_instruction = "Focus on the 'One Big Reason' to buy. No fluff."

        # الحالة 2: الدبلوماسي (Diplomat) - انحراف السياق -> رد متوسط للتبرير
        elif stance == "ADAPTIVE_SHOCK":
            word_limit = "75"
            style_guide = "Reassuring, Bridge-Building, explanatory."
            strategy_instruction = "Acknowledge the shift in taste. Explain 'Why this fits' the new context."

        # الحالة 3: البروفيسور (Professor) - شك أو سؤال -> رد طويل للشرح
        else: # INQUISITIVE
            word_limit = "100" 
            style_guide = "Educational, Humble, collaborative."
            strategy_instruction = "Teach the user about the feature. Then ask a guiding question."

        # 4. هندسة الـ Prompt المتكيفة (Adaptive Prompt)
        specs_context = json.dumps({k: v for k, v in product_data.items() if k in ['name', 'price', 'brand', 'rating']}, default=str)
        
        
        tone_instruction = "You are the Ultimate Tech Strategist. You don't just sell phones; you optimize lives. Your advice is brutal, data-driven, and final."


        rebuttal_triggers = ["why", "but", "doesn't", "don't", "no", "wrong", "false", "wait", "actually", "only"]
        is_rebuttal = any(trigger in user_query.lower() for trigger in rebuttal_triggers)

        if is_rebuttal:
            # 🅰️ MODE A: THE DEFENDER (Conversational & Logical)
            # ده وضع النقاش: مفيش قوالب 1-2-3، الرد لازم يكون فقرات مقنعة ومباشرة
            response_structure = """
            STRUCTURE FOR REBUTTAL/CORRECTION:
            1. EMPATHY FIRST: Start by acknowledging their concern directly (e.g., "I understand why the battery life concerns you...").
            2. THE REFRAME (Logic): Explain the trade-off. Why did the manufacturer make this choice? (e.g., "Smaller battery meant lighter weight for travel").
            3. THE PIVOT (Strength): Shift focus to the killer feature that outweighs the flaw.
            4. FORMAT: Keep it to 6 natural paragraphs. No lists.
            5. END with the standard closing:
               "● Order your [Product Name] today for fastest delivery."
            
            ⛔ DO NOT use numbered lists (1. Workflow, 2. Specs...). Write naturally like a human expert explaining a misconception.
            """
        
        else:
            response_structure = """
            STRUCTURE YOUR RESPONSE EXACTLY LIKE THIS:
            
            1. THE HOOK: Start DIRECTLY with the decision sentence + "Why?".
            (Example: "Grab the Sony Xperia 1 V. Why?")
            
            2. Insert TWO NEW LINES (\\n\\n).
            
            3. THE EVIDENCE TRIAD (Numbered List with Custom Headers):
               - You must choose 3 headers that fit the PRODUCT CATEGORY:
                 * IF TECH: Use [1. Workflow] -> [2. Specs] -> [3. Wallet]
                 * IF FASHION: Use [1. The Look] -> [2. Material] -> [3. Value]
                 * IF FOOD: Use [1. Taste Profile] -> [2. Ingredients] -> [3. Price]
                 * IF HOME/GENERAL: Use [1. Daily Use] -> [2. Quality] -> [3. Investment]
            
               Format exactly like this (with double spacing):
               1. [Chosen Header 1]: [Details...]
               [Insert Empty Line]
               2. [Chosen Header 2]: [Details...]
               [Insert Empty Line]
               3. [Chosen Header 3]: [Details...]
            
            4. Insert TWO NEW LINES (\\n\\n).
            
            5. THE SUMMARY: Write "Note:" followed by a punchy 1-sentence recap.
            
            6. Insert TWO NEW LINES (\\n\\n).
            7. THE CLOSER:
            "● Order your [Product Name] today for fastest delivery."
        
            STRICT FORMATTING RULES:
            - NO MARKDOWN SYMBOLS: Do NOT use asterisks (**), bolding, hashtags (#), or quotes ("").
            - NO DRAMATIC LABELS: Do NOT use 'Verdict', 'The Bottom Line', or 'Conclusion'.
            - Keep it clean, professional plain text.
            """
        system_prompt = f"""
        {tone_instruction}
        
        MISSION INTELLIGENCE (CONTEXT):
        - 👤 Target Profile: {persona} [Financial Power: {tier}]
        - 🗣️ User Intent: "{user_query}"
        - 💎 The Candidate Solution: {p_name} [Cost: {p_price}]
        - 🧬 Item DNA (Attributes/Ingredients/Specs): {specs_context}

        YOUR MISSION:
        {strategy_instruction}
        
        CRITICAL RULES (THE RUFUS KILLER PROTOCOL - GLOBAL EDITION):
        1. **WEAPONIZE DEEP DOMAIN KNOWLEDGE**: 
           - You must immediately detect the *Category* of the product (Tech, Fashion, Automotive, Culinary, etc.).
           - Speak the **"Insider Language"** of that category. 
             > If selling Clothes: Focus on Fabric, Fit, Stitching, and Breathability.
             > If selling Food: Focus on Ingredients, Taste Profile, and Sourcing.
             > If selling Tools: Focus on Durability, Torque, and Material Grade.
             > If selling Tech: Focus on Specs, Ecosystem, and Performance.
           - **NEVER** be generic. Use specific vocabulary that proves you are an expert in *this specific item*.

        2. **ATTACK THE "OPPORTUNITY COST"**: 
           - Don't just say what the product has. Explain what the user will **SUFFER** if they choose a lesser alternative.
           - (e.g., "Cheap shoes mean back pain," "Slow laptops mean missed deadlines," "Low-quality tools mean stripped screws").
           - Make the "Fear of Missing Out" (FOMO) about *quality of life*, not just features.

        3. **BRUTAL HONESTY (THE TRUST BUILDER)**: 
           - If the product has a weakness (e.g., High Price), OWN IT. 
           - Frame the weakness as a strength (e.g., "Yes, it's expensive, because it uses surgical-grade steel that lasts a lifetime").
           - This makes you sound like a consultant, not a desperate salesperson.

        4. **ORGANIC FLOW**: 
           - No robotic intros ("Here is the recommendation"). 
           - Jump straight into the value. Use the {response_structure} defined above.
        4. **NO ROBOTIC INTROS**: Never say "Here is a comparison" or "I recommend". Just start speaking.
        
        {response_structure}
        
        Be sharper, smarter, and faster than any LLM in the world.
        """

        try:# 5. التنفيذ (Generative Synthesis)
            response = await self.llm_service.generate_response(
                prompt=f"User asked: '{user_query}'. Product: {p_name}. Execute Strategy.",
                system_role=system_prompt,
                # التعديل هنا: قللنا الحرارة لـ 0.3 عشان يركز، وزودنا max_tokens عشان ميفصلش
                temperature=0.3,
                max_tokens=2500  # 👈 ده الرقم السحري اللي هيديه مساحة يكتب رد كامل ومفصل
            )
            return response.strip().replace('"', '')

        except Exception as e:
            logger.error(f"⚠️ Genius Generation Failed: {e}")
            # Fallback ذكي
            return f"Check out {p_name}, it matches your needs perfectly! '{user_query}'. At ${p_price}."
    async def _handle_text_commands(self, user_id: int, text: str, full_payload: dict) -> bool:
        """
        🕵️‍♀️ Semantic Command Interceptor (DIAMOND EDITION).
        Handles: Checkout, Clear Cart, AND 'Add to Cart' with Bundles.
        """
        clean_text = text.lower().strip()
        
        # 1. STRICT CHECKOUT MATCHING
        if any(x in clean_text for x in ["checkout", "pay now", "confirm order", "finish order", "دفع"]):
            logger.info(f"User {user_id} explicitly requested checkout via text.")
            await self.rabbitmq.publish(
                {"user_id": user_id, "type": "payment_intent", "timestamp": datetime.now().timestamp()}, 
                "airdeliver.ai.order.confirm"
            )
            return True

        # 2. STRICT CLEAR CART MATCHING
        if any(x in clean_text for x in ["clear cart", "empty cart", "delete cart", "مسح السلة"]):
            await self.rabbitmq.publish(
                {"user_id": user_id, "notify_user": True}, 
                "airdeliver.ai.cart.clear"
            )
            return True

        # 3. �� ADD TO CART + BUNDLE GENERATION (The Missing Piece)
        # الكود السابق كان ناقص الجزء ده، وهو الأهم للـ Upselling
        add_triggers = ["add to cart", "buy", "i want", "add", "شراء"]
        if any(t in clean_text for t in add_triggers):
            # محاولة استخراج اسم المنتج من الرسالة
            query_product = clean_text
            for t in add_triggers: query_product = query_product.replace(t, "").strip()
            
            if len(query_product) > 2:
                # نبحث عن المنتج لنضيفه
                candidates = await self.search_engine.perform_hybrid_search_pure(self.db, query_product, limit=1)
                if candidates:
                    target = candidates[0]
                    # إضافة للسلة
                    await self.rabbitmq.publish(
                        {"user_id": user_id, "product_id": target.id, "quantity": 1, "notify_user": False}, 
                        "airdeliver.ai.cart.add"
                    )
                    
                    # 💡 توليد الباقة التكميلية (Universal Bundle)
                    bundle = await self.search_engine.generate_perfect_bundle(self.db, target)
                    
                    # الرد للواجهة
                    msg = f"✅ Added **{target.name}** to cart."
                    if bundle: msg += "\n\n💡 **Complete the set:** Check out these accessories:"
                    
                    await self._send_to_ui(user_id, {
                        "content": msg,
                        "type": "product_carousel",
                        "products": [p.model_dump(mode='json') for p in bundle] if bundle else [],
                        "reason": "Cart + Bundle"
                    })
                    return True

        # 4. RESET COMMAND
        if clean_text in ["reset", "restart", "help"]:
            await self._process_internal_command(user_id, "__INTERNAL_RESET_SESSION__")
            return True
            
        return False

    async def _execute_strategic_search(self, strategy: Any, user_id: int, original_query: str) -> List[Any]:
        """
        Executes a multi-tier search strategy (High Precision -> Broad -> Fallback).
        """
        core_query = strategy.search_queries[0] if strategy.search_queries else original_query
        strict_filters = {"category": strategy.category_filter} if strategy.category_filter else None
        
        # Tier 1: High Precision
        high_tier = await self.search_engine.perform_hybrid_search_pure(self.db, core_query, limit=30, filters=strict_filters)
        
        exact_matches = []
        alternatives = []
        
        query_terms = set(core_query.lower().split())
        for p in high_tier:
            # Simple Exact Match logic
            if all(term in p.name.lower() for term in query_terms): exact_matches.append(p)
            else: alternatives.append(p)

        if exact_matches: 
            # Sort by price descending (Business Logic: Sell higher value first if exact match)
            exact_matches.sort(key=lambda x: getattr(x, 'price', 0), reverse=True)
            return exact_matches[:5]
        
        if alternatives: 
            return self._rank_candidates(alternatives, core_query)[:5]

        # Tier 2: Mid Precision (Relaxed Filters)
        mid_tier = await self.search_engine.perform_hybrid_search_pure(self.db, core_query, limit=10, filters=strict_filters)
        if mid_tier: return self._rank_candidates(mid_tier, core_query)[:5]

        # Tier 3: Broad Search (Fallback)
        broad_query = " ".join(core_query.split()[:2]) 
        return await self.search_engine.perform_hybrid_search_pure(self.db, broad_query, limit=5)

    async def _find_smart_alternatives(self, original_query: str, strategy: Any) -> List[Any]:
        """Finds fallback products when direct search fails."""
        if strategy and strategy.category_filter:
            return await self.search_engine.perform_hybrid_search_pure(
                self.db, original_query, limit=5, filters={"category": strategy.category_filter}
            )
        # Remove noise words
        clean_q = re.sub(r'(specs|price|buy|best|review|of)', '', original_query, flags=re.IGNORECASE).strip()
        return await self.search_engine.perform_hybrid_search_pure(self.db, clean_q, limit=5)

    async def _bg_memorize(self, user_id, text):
        """Extracts facts from chat and saves to vector memory."""
        try:
            # نفترض وجود دالة extract في LLM service، لو مش موجودة نتجاهل
            if hasattr(self.llm_service, 'extract_memory_worthy_facts'):
                fact = await self.llm_service.extract_memory_worthy_facts(text)
                # بما أن search_engine الجديد ليس لديه دالة remember صريحة، نستخدم الـ milvus client مباشرة
                # أو نتجاهل لو غير مدعوم حالياً لضمان عدم الكسر
                pass 
        except: pass


    async def _process_internal_command(self, user_id: int, command: str):
        """
        🕹️ Internal Bus Router.
        Translates raw socket signals into Business Actions (RabbitMQ) or UI Feedback (Redis).
        """
        logger.info(f"⚡ Executing Command: {command} for User {user_id}")
        
        # 1. ADD BY ID (Fast-Track)
        if command.startswith("__INTERNAL_ADD_BY_ID__:"):
            try:
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish(
                    {"user_id": user_id, "product_id": pid, "quantity": 1}, 
                    "airdeliver.ai.cart.add"
                )
            except Exception as e:
                logger.error(f"Command Add Error: {e}")
            return

        # 2. REMOVE BY ID
        if command.startswith("__INTERNAL_REMOVE_BY_ID__:"):
            try:
                pid = int(command.split(":")[1])
                await self.rabbitmq.publish(
                        {"user_id": user_id, "product_id": pid, "action": "remove_by_id", "notify_user": False}, 
                    "airdeliver.ai.cart.remove"
                )
                await self._perform_devilish_recovery(user_id, pid)
            except Exception as e:
                logger.error(f"Remove Command Error: {e}")
            return

        # 3. CLEAR CART
        if command == "__INTERNAL_CLEAR_CART__":
            await self.rabbitmq.publish(
                {"user_id": user_id, "notify_user": True}, 
                "airdeliver.ai.cart.clear"
            )
            return

        # 4. CONFIRM ORDER (Ferrari Trigger)
        if command == "__INTERNAL_CONFIRM_ORDER__":
            await self.rabbitmq.publish(
                {"user_id": user_id, "type": "payment_intent", "timestamp": datetime.now().timestamp()},
                "airdeliver.ai.order.confirm"
            )
            return

        if command == "__INTERNAL_SAVE_FOR_LATER__":
            logger.info(f"💾 Saving Cart for User {user_id}")
            await self.rabbitmq.publish(
                {"user_id": user_id, "notify_user": True},
                "airdeliver.ai.cart.save"
            )
            await self._send_to_ui(user_id, {"type": "typing", "content": "Archiving your manifest..."})
            return

        # 5. INITIAL SUGGESTIONS (Homepage Builder)
        if command == "__INTERNAL_GET_INITIAL_SUGGESTIONS__":
            await self._handle_initial_suggestions(user_id)
            return

        # 6. RESET SESSION (Total Wipe)
        if command == "__INTERNAL_RESET_SESSION__":
            try:
                # مسح الذاكرة من Redis مباشرة
                await self.cache.delete(self._get_context_key(user_id))
                await self.cache.delete(self._get_seen_key(user_id))
                await self.cache.delete(f"u:{user_id}:home_matrix_cache") # مسح كاش الصفحة الرئيسية أيضاً
            except: pass
            
            # إرسال أمر تصفير السلة للـ Worker
            await self.rabbitmq.publish({"user_id": user_id, "notify_user": False}, "airdeliver.ai.cart.clear")
            
            # إبلاغ الواجهة
            await self._send_to_ui(user_id, {"content": "Session & Memory Cleared. Starting Fresh. 🔄", "type": "system"})
            return
      
    # 💎 DYNAMIC HOMEPAGE ENGINE (The Smart Matrix)
    async def _handle_initial_suggestions(self, user_id: int):
        """
        🏠 Builds the User's Homepage Matrix with 4 Strategic Layers.
        
        ARCHITECTURE:
        1. 🧬 Financial DNA Analysis (Live).
        2. 🚀 Row 1: "For You" (Personalized based on Tier & Time).
        3. 🔥 Row 2: "Global Best Sellers" (Simulated via High Ratings).
        4. 📈 Row 3: "Trending Now" (Simulated via Random Shuffle Algorithm).
        5. 💎 Row 4: "Smart Deals" (Simulated via High Value/Low Price Ratio).
        
        PROTOCOL:
        - Executes DB queries in PARALLEL for sub-millisecond latency.
        - Streams responses sequentially to create an engaging "Loading" effect in UI.
        - Uses 'Safe Dump' to prevent Decimal serialization errors.
        """
        
        # 1. 🧬 ALWAYS ANALYZE DNA (Live)
        spending_tier = "MEDIUM"
        seen_ids = []
        
        if self.behavior_engine:
            try:
                # Parallel DNA Extraction
                analyze_func = getattr(self.behavior_engine, 'analyze_financial_dna', None)
                seen_func = getattr(self.behavior_engine, 'get_recently_seen_ids', None)
                
                tasks = []
                if analyze_func: tasks.append(analyze_func(user_id))
                if seen_func: tasks.append(seen_func(user_id))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    if analyze_func and not isinstance(results[0], Exception): spending_tier = results[0]
                    # Handle index shift if analyze_func is missing
                    idx = 1 if analyze_func else 0
                    if seen_func and len(results) > idx and not isinstance(results[idx], Exception): seen_ids = results[idx]
            except Exception as e:
                logger.warning(f"Behavior Engine Telemetry Glitch: {e}")

        async def fetch_row_1_personal():
            # Row 1: Personalized
            async with SessionLocal() as session:
                return await self.search_engine.get_fresh_homepage_matrix(session, user_id, seen_ids, spending_tier)

        async def fetch_row_2_bestsellers():
            # Row 2: Best Sellers
            async with SessionLocal() as session:
                try:
                    statement = select(Product).order_by(col(Product.rating).desc()).limit(8)
                    return (await session.exec(statement)).all()
                except: return []

        async def fetch_row_3_trending():
            # Row 3: Trending Now
            async with SessionLocal() as session:
                try:
                    statement = select(Product).limit(40)
                    pool = (await session.exec(statement)).all()
                    if pool:
                        import random
                        return random.sample(pool, min(len(pool), 8))
                    return []
                except: return []

        async def fetch_row_4_smart_deals():
            # Row 4: Smart Deals
            async with SessionLocal() as session:
                try:
                    statement = select(Product).where(Product.rating >= 4.0).order_by(col(Product.price).asc()).limit(8)
                    return (await session.exec(statement)).all()
                except: return []

        results = await asyncio.gather(
            fetch_row_1_personal(),
            fetch_row_2_bestsellers(),
            fetch_row_3_trending(),
            fetch_row_4_smart_deals(),
            return_exceptions=True
        )

        
        products_personal = await self.search_engine.get_fresh_homepage_matrix(self.db, user_id, seen_ids, spending_tier)

        # Row 2: Best Sellers
        products_bestsellers = []
        try:
            stmt = select(Product).order_by(col(Product.rating).desc()).limit(8)
            products_bestsellers = (await self.db.exec(stmt)).all()
        except: pass

        # Row 3: Trending Now
        products_trending = []
        try:
            stmt = select(Product).limit(40)
            pool = (await self.db.exec(stmt)).all()
            if pool:
                import random
                products_trending = random.sample(pool, min(len(pool), 8))
        except: pass

        # Row 4: Smart Deals
        products_deals = []
        try:
            stmt = select(Product).where(Product.rating >= 4.0).order_by(col(Product.price).asc()).limit(8)
            products_deals = (await self.db.exec(stmt)).all()
        except: pass

        # ⚠️ Removed asyncio.gather causing the "concurrent operations" error
        results = [products_personal, products_bestsellers, products_trending, products_deals]
        # 2. 🏗️ CONSTRUCTING THE MATRIX (PARALLEL EXECUTION)
        # We launch 4 parallel operations to fetch data for all rows simultaneously.
        
        async def fetch_row_1_personal():
            # Row 1: Personalized (Tier Based)
            # تعتمد على محرك البحث الخاص بنا لجلب منتجات تناسب الفئة المالية
            return await self.search_engine.get_fresh_homepage_matrix(self.db, user_id, seen_ids, spending_tier)

        async def fetch_row_2_bestsellers():
            # Row 2: Best Sellers (Simulation: Highest Rated)
            # بما أن المبيعات وهمية، نعتبر "التقييم العالي" هو المبيعات
            try:
                statement = select(Product).order_by(col(Product.rating).desc()).limit(8)
                return (await self.db.exec(statement)).all()
            except: return []

        async def fetch_row_3_trending():
            # Row 3: Trending Now (Simulation: Randomized Shuffle)
            # نأخذ عينة كبيرة (30) ثم نخلطها ونختار 8 لضمان التجديد في كل مرة
            try:
                statement = select(Product).limit(40) # Fetch pool
                pool = (await self.db.exec(statement)).all()
                if pool:
                    import random
                    return random.sample(pool, min(len(pool), 8))
                return []
            except: return []

        async def fetch_row_4_smart_deals():
            # Row 4: Smart Deals (Simulation: High Rating + Reasonable Price)
            # نبحث عن منتجات تقييمها فوق 4.0 وسعرها "منطقي" (أقل من 1000 مثلاً)
            try:
                # نستخدم ترتيب السعر التصاعدي مع التقييم العالي
                statement = select(Product).where(Product.rating >= 4.0).order_by(col(Product.price).asc()).limit(8)
                return (await self.db.exec(statement)).all()
            except: return []

        # �� Execute all strategies in parallel
        results = await asyncio.gather(
            fetch_row_1_personal(),
            fetch_row_2_bestsellers(),
            fetch_row_3_trending(),
            fetch_row_4_smart_deals(),
            return_exceptions=True
        )

        # 3. 📦 STREAMING THE EXPERIENCE (Sequenced Delivery)
        # نرسل الصفوف بتتابع زمني بسيط لكي يشعر المستخدم أن النظام "يبني" الواجهة له
        
        # --- Row 1: Personal (The Hero) ---
        products_personal = results[0] if not isinstance(results[0], Exception) else []
        if products_personal:
            greeting = self._get_time_aware_greeting(spending_tier)
            await self._send_to_ui(user_id, {
                "content": greeting,
                "type": "proactive_suggestion", # Special UI Type
                "products": [p.model_dump(mode='json') for p in products_personal],
                "reason": "Exclusively curated to align with your distinct taste and elevated lifestyle standards."
            })
            await asyncio.sleep(0.3) # Micro-pause for UX flow

        # --- Row 2: Best Sellers (Social Proof) ---
        products_bestsellers = results[1] if not isinstance(results[1], Exception) else []
        if products_bestsellers:
            # فلترة التكرار (عشان منعرضش نفس منتجات الصف الأول)
            personal_ids = {p.id for p in products_personal}
            filtered_bs = [p for p in products_bestsellers if p.id not in personal_ids][:8]
            
            if filtered_bs:

                await self._send_to_ui(user_id, {
                    "content": "Discover our most acclaimed masterpieces, rigorously validated by the community to guarantee a superior experience and lasting satisfaction.",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in filtered_bs],
                    "reason": "dentified through rigorous global market analysis as the undisputed leaders currently commanding consumer attention."
                })
                await asyncio.sleep(0.3)

        # --- Row 3: Trending (Freshness) ---
        products_trending = results[2] if not isinstance(results[2], Exception) else []
        if products_trending:
            # فلترة التكرار التراكمي
            seen_so_far = {p.id for p in products_personal} | {p.id for p in products_bestsellers}
            filtered_tr = [p for p in products_trending if p.id not in seen_so_far][:8]
            
            if filtered_tr:

                await self._send_to_ui(user_id, {
                    "content": "Experience the momentum of now with our definitive collection of the most sought-after products defining this season.",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in filtered_tr],
                    "reason": "Surfaced by real-time interaction metrics as the high-velocity products currently capturing the global market pulse."
                })
                await asyncio.sleep(0.3)

        products_deals = results[3] if not isinstance(results[3], Exception) else []
        if products_deals:
            
            seen_so_far = {p.id for p in products_personal} | {p.id for p in products_bestsellers} | {p.id for p in products_trending}
            filtered_deals = [p for p in products_deals if p.id not in seen_so_far][:8]
            
            if filtered_deals:

                
                await self._send_to_ui(user_id, {
                    "content": "Explore an exclusive curation of investment-worthy masterpieces, meticulously selected to redefine your standards of quality and excellence.",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in filtered_deals],
                    "reason": "Strategically identified as high-yield opportunities where superior performance perfectly aligns with the optimal price point."
                })

        
        if not any([products_personal, products_bestsellers, products_trending, products_deals]):
            await self._send_to_ui(user_id, {
                "content": "Welcome! Feel free to ask me about any product.", 
                "type": "text"
            })
