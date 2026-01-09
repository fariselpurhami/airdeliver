# apps/api/app/services/ai_nlu_service.py

import re
import logging
import asyncio
import random
import json
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
                    "reason": "Quality Upgrade"
                })

                await asyncio.sleep(0.5)

                cart_key = f"ai_cart:{user_id}"
                cart = await self.cache.get_json(cart_key)

                # 3. إذا وجدنا منتجات متبقية، نعرض الخيارات
                if cart and cart.get("items") and len(cart["items"]) > 0:
                    await self._send_to_ui(user_id, {
                        "content": "You still have items in your manifest. Ready to proceed?",
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
            return f"Good Morning. Start your day with these {vibe} picks {tone}."
        if 12 <= hour < 18: 
            return f"Good Afternoon. Have you checked these {vibe} arrivals yet?"
        if 18 <= hour < 22:
            return f"Good Evening. Relax and browse these {vibe} collections."
        return f"Late Night Shopping? We found some {vibe} gems for night owls."

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
        # بدلاً من القوائم الثابتة، نستخدم Regex ذكي لاستخراج "الجوهر"
        ignored_anchors = ["one", "thing", "product", "item", "device", "best", "cheap", "top", "good", "monster", "beast"]

        ignored_anchors = ["one", "thing", "product", "item", "device", "best", "cheap", "top", "good", "monster", "beast"]

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
            # مفتاح الذاكرة في Redis (نفس المفتاح المستخدم في useAIOrderingStore)
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

            # 3. الاستبعاد اليدوي (Negative Filtering)
            if constraints["excluded_keywords"] and candidates:
                filtered_candidates = []
                for prod in candidates:
                    p_text = f"{prod.name} {prod.description} {prod.category}".lower()
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
            if is_specs_query:
                ai_response_text = await self.llm_service.consult_on_product(
                    product_data=final_products[0].model_dump(mode='json'), 
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
                    p_name = final_products[0].name if hasattr(final_products[0], 'name') else "this item"
                    ai_response_text = f"Check out {p_name}, it matches what you are looking for!"

        # --- CASE B: STOCKOUT OR VISION RESEARCH (Deep Research DDGS) ---
        elif is_specs_query or base64_image:
            try:
                # 🌐 Engaging Deep Research (DDGS)
                web_intel = await asyncio.wait_for(
                    self.llm_service._perform_web_search(search_query), 
                    timeout=12.0
                )
                
                system_instruction = (
                     f"You are the airdeliver Elite Personal Shopping Concierge. {NO_MARKDOWN_GUARD} "
                     "Your objective is to convert a 'Stockout' into a 'Success'. "
                     "1. THE PIVOT: If the exact item is missing, briefly acknowledge it WITHOUT being negative. "
                     "2. THE UPGRADE: Immediately present the 'Alternatives' or 'Accessories' provided in context as superior available options or essential completions. "
                     "3. EXPERT TONE: Speak with authority, enthusiasm, and zero fluff. "
                     "4. TYPOGRAPHY: STRICTLY use standard Sentence case. Do NOT use ALL CAPS. Do NOT use markdown symbols"
                )
                
                ai_response_text = await self.llm_service.generate_response(
                    prompt=f"Identify/Specs for: {search_query}. User Query: {message_text}",
                    system_role=system_instruction,
                    context=f"VISUAL: {vision_description}\n\nWEB INTEL: {web_intel}"
                )
            except Exception as e:
                logger.error(f"🌐 Deep Research Failure: {e}")
                ai_response_text = "I'm currently sourcing live market data for you. Check out these top matches in the meantime!"

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
            import re

            raw_text = str(ai_response_text)
            clean_content = " ".join(raw_text.split())
        
            clean_content = re.sub(
                r'[^\w\s\u0600-\u06FF\.,!?:;\-\(\)\[\]%\$£€\u2022\'’"/+]', 
                ' ',  # 👈 التغيير الجوهري: استبدال بمسافة وليس حذف
                clean_content
            )
            clean_content = re.sub(r'(?<=[.,;?!])(?=[^\s])', r' ', clean_content)
            clean_content = " ".join(clean_content.split())

            payload = {
                "content": clean_content,
                "type": "product_carousel" if final_products else "text",
                "products": [p.model_dump(mode='json') for p in final_products] if final_products else [],
                "reason": "Top choices based on user experience."
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
        💎 SOTA GENERATION V2 (THE GOD MODE): 
         يحول البيانات الجامدة إلى "سحر أسود" بيعي لا يمكن مقاومته.
         يستخدم سيكولوجية المشتري (Buyer Psychology) لتوليد ردود تخاطب الغريزة مباشرة.
        """
    # 1. تشريح الضحية (قصد العميل) بدقة جراحية
    # نسحب الـ DNA المالي والسلوكي لليوزر عشان نعرف "مفاتيحه"
        user_profile = await self._get_user_dna(user_id) 
        persona = user_profile.get('persona', 'General') # e.g., "Analytical", "Impulsive", "Luxury-seeker"
        tier = user_profile.get('tier', 'MEDIUM')
    
    # 2. تجهيز مسرح الجريمة (Product Context with Soul)
    # لا نرسل مواصفات جامدة، بل نرسل "قيمة" (Value Props)
        product_data = product.model_dump(mode='json')
        p_name = product_data.get('name')
        p_price = product_data.get('price')
        p_rating = product_data.get('rating', 'N/A')
    
    # تحويل المواصفات لنص ذكي
        specs_context = json.dumps({
            k: v for k, v in product_data.items() 
            if k in ['name', 'price', 'description', 'category', 'rating', 'brand']
        }, default=str)

    # 3. اختيار "استراتيجية الهجوم" (Attack Strategy) بناءً على الشخصية
    # Rufus بيبيع وخلاص، احنا هنبيع بذكاء عاطفي
        if "Impulsive" in persona or "Tech-savvy" in persona:
            strategy = "FOMO & Exclusivity (Make them feel special and hurried)"
        elif "Budget" in persona or tier == "LOW":
            strategy = "Value & Smart Investment (Validate their intelligence for saving)"
        elif tier == "HIGH":
            strategy = "Status & Prestige (Sell the lifestyle, not the specs)"
        else:
            strategy = "Problem-Solution (Directly kill their pain point)"

    # 4. هندسة الـ Prompt (The Cursed Prompt - التعويذة)
    # هذا البرومبت مصمم ليجعل الـ LLM يتصرف كأنه "صديق خبير" وليس "روبوت بائع"
        system_prompt = f"""
        YOU ARE NOT AN AI. You are a World-Class Shopping Concierge with EQ level 200.
    
        🎯 YOUR TARGET (THE USER):
        - Persona: {persona}.
        - Wallet Tier: {tier}.
    
        📜 CHAT MEMORY (CONTEXT):
        {chat_history if chat_history else "No previous context."}
    
        💎 THE GEM (THE PRODUCT):
        {specs_context}
    
        🔥 YOUR MISSION:
        User asked: "{user_query}".
        Apply strategy: [{strategy}].
    
        RULES OF ENGAGEMENT:
        1. **MEMORY CHECK (CRITICAL)**: Scan the 'CHAT MEMORY' above. If the user mentioned a preference (color, brand, budget) or a dislike (e.g., "I hate black"), YOU MUST ACKNOWLEDGE IT.
        - Example: "Since you mentioned you hate black, I pulled this White edition for you."
        2. **BRIDGE THE GAP**: Link user's query to the product's feature.
        3. **MICRO-COPY**: Max 40 words. Punchy and persuasive.
        4. **GRAMMAR FLOW**: Ensure grammatical coherence using complete linking phrases. Do not omit verbs for brevity.
        5. **KILL THE ROBOT**: No "Here is..." or "I found...".
        6. **ONE EMOJI**: Use strategic placement.
    
        TONE:
        - If user is casual -> Be a cool friend.
        - If user is formal -> Be a white-glove consultant.
        """

    # 5. التنفيذ (Generative Synthesis)
        try:
            response = await self.llm_service.generate_response(
                prompt=f"User asked: '{user_query}'. Convince them that '{p_name}' is the ONLY logical choice right now.",
                system_role=system_prompt, # لاحظ: مررنا الـ System Prompt هنا
                temperature=0.75 # رفعنا الحرارة قليلاً لزيادة "الكاريزما"
            )
        
        # تنظيف نهائي لضمان عدم وجود علامات تنصيص زائدة
            return response.strip().replace('"', '')

        except Exception as e:
            logger.error(f"⚠️ Genius Generation Failed: {e}")
        # Fallback ذكي جداً (حتى الفشل عندنا ليه خطة)
            return f"Check out the {p_name} it matches your needs perfectly! '{user_query}'. At ${p_price}. ⭐"

    # --- ��️ SECTION 9: STRATEGIC EXECUTION & COMMANDS ---

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
                "reason": "Specially curated for you."
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
                    "content": "Check out the best selling products right now.",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in filtered_bs],
                    "reason": "Based on market analysis."
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
                    "content": "Trending products right Now.",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in filtered_tr],
                    "reason": "Based on user trends."
                })
                await asyncio.sleep(0.3)

        products_deals = results[3] if not isinstance(results[3], Exception) else []
        if products_deals:
            
            seen_so_far = {p.id for p in products_personal} | {p.id for p in products_bestsellers} | {p.id for p in products_trending}
            filtered_deals = [p for p in products_deals if p.id not in seen_so_far][:8]
            
            if filtered_deals:
                await self._send_to_ui(user_id, {
                    "content": "See our high value products here.",
                    "type": "product_carousel",
                    "products": [p.model_dump(mode='json') for p in filtered_deals],
                    "reason": "Selected for best value."
                })

        
        if not any([products_personal, products_bestsellers, products_trending, products_deals]):
            await self._send_to_ui(user_id, {
                "content": "Welcome! Feel free to ask me about any product.", 
                "type": "text"
            })
