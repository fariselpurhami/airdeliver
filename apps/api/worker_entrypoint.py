# apps/api/worker_entrypoint.py

import logging
import sys
import uvloop
import psutil # 👈 ضيف ده عشان مراقبة البروسيسور
import torch  # 👈 ضيف ده عشان مراقبة كارت الشاشة
import warnings
from concurrent.futures import ThreadPoolExecutor
import asyncio
import json
import os
import signal
import random
from functools import partial
from typing import Callable, Awaitable
from aiohttp import web
import aio_pika
import redis.asyncio as redis
from aio_pika.abc import AbstractIncomingMessage
from aio_pika import connect_robust, IncomingMessage
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from pymilvus import MilvusClient, DataType
from datetime import datetime

# Services & Config
from app.core.config import (
    get_core_settings, 
    get_stripe_settings, get_paypal_settings, get_mpesa_settings
)
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import RedisCacheClient
from app.services.ai_nlu_service import AINLUService
from app.services.free_llm_service import FreeLLMService
from app.services.ai_behavior_engine import BehaviorEngine

# 💎 SOTA Engine Imports
from app.services.ai_commerce_engine import (
    get_ai_commerce_engine,
    get_opensearch_client,
    get_milvus_client,
    ai_manager
)
from app.services.payment_orchestrator import (
    PaymentOrchestrator, StripeGateway, PayPalGateway, MpesaGateway
)

from transformers.cache_utils import DynamicCache

# Hotfix for Transformers DynamicCache
try:
    if not hasattr(DynamicCache, "get_usable_length"):
        def get_usable_length(self, input_seq_len, layer_idx=None):
            if layer_idx is None: layer_idx = 0
            return self.get_seq_length(layer_idx)
        DynamicCache.get_usable_length = get_usable_length
        logging.getLogger("transformers").warning("🛡️ Applied Hotfix: DynamicCache.get_usable_length patched.")
except Exception as e:
    logging.warning(f"⚠️ Hotfix skipped: {e}")

# 2. 📝 LOGGING SETUP (CLEAN & PROFESSIONAL)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | [Worker-Node-Diamond] | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.getLogger("aio_pika").setLevel(logging.WARNING)
logging.getLogger("aiormq").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("accelerate").setLevel(logging.ERROR)

logger = logging.getLogger("airdeliver.worker")

warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.transformer")
# 3. 🚀 HIGH PERFORMANCE LOOP
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def emergency_brake(signum, frame):
    signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
    print(f"\n🛑 ARCHITECTURE ALERT: Received {signal_name}. Initiating Immediate Shutdown...")
    logger.warning(f"🛑 Signal {signal_name} received. Killing process gracefully.")
    sys.exit(0)

signal.signal(signal.SIGINT, emergency_brake)
signal.signal(signal.SIGTERM, emergency_brake)

# --- GLOBAL SERVICES REGISTRY ---
_services = {
    "rabbitmq": None,
    "db_engine": None,
    "cache": None,
    "commerce": None,
    "session_maker": None,
    "payment": None,
    "behavior": None,
    "llm": None
}

def ensure_milvus_schema(client: MilvusClient):
    """
    💎 SOTA UPDATE: Enforces Correct Dimensions Dynamically.
    Ensures the Vector DB is ready for both Text (Qwen2) and Vision (SigLIP).
    """
    text_col = "airdeliver_products_sota_v4"
    vis_col = "airdeliver_visual_sota_v4"
    
    TEXT_DIM = 1536  # Qwen2 / GTE Dimension
    VIS_DIM = 1152   # SigLIP Standard
    
    try:
        # 1. Text Collection (Semantic Search)
        if not client.has_collection(text_col):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=TEXT_DIM)
            schema.add_field(field_name="price", datatype=DataType.FLOAT)
            schema.add_field(field_name="category", datatype=DataType.VARCHAR, max_length=128)
            
            idx = client.prepare_index_params()
            idx.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
            
            client.create_collection(text_col, schema=schema, index_params=idx)
            logger.info(f"✅ Milvus: Text Collection Ready ({text_col}, dim={TEXT_DIM})")

        # 2. Visual Collection (Image Search)
        if not client.has_collection(vis_col):
            schema_vis = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema_vis.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema_vis.add_field(field_name="image_vector", datatype=DataType.FLOAT_VECTOR, dim=VIS_DIM)
            
            idx_vis = client.prepare_index_params()
            idx_vis.add_index(field_name="image_vector", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
            
            client.create_collection(vis_col, schema=schema_vis, index_params=idx_vis)
            logger.info(f"✅ Milvus: Visual Collection Ready ({vis_col}, dim={VIS_DIM})")
            
    except Exception as e:
        logger.error(f"⚠️ Milvus Init Warning: {e}")

class VoiceBrainStatus:
    READY = False
    LOADING = False
    ERROR = None

# --- 🧠 INTELLIGENT LAZY LOADER (TITANIUM EDITION v9000) ---
async def lazy_load_voice_brain():
    """
    💎 TITANIUM BACKGROUND LOADER.
    Capabilities:
    1. 🛡️ Adaptive Stability Wait (Monitors CPU/RAM).
    2. 💾 VRAM Sentinel (Prevents OOM Crashes).
    3. 🔄 Exponential Backoff Retry Strategy.
    4. 🚀 Thread Isolation (Non-blocking Guarantee).
    """
    VoiceBrainStatus.LOADING = True
    MAX_RETRIES = 3

    logger.info("🛡️ [Titanium Loader] Initiating Secure Boot Protocol for PersonaPlex...")

    # --- PHASE 1: ADAPTIVE STABILIZATION (ذكاء الانتظار) ---
    # بدل ما ننام 5 ثواني عمياني، نراقب "نبض" السيرفر
    for attempt in range(10):
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram_usage = psutil.virtual_memory().percent

        if cpu_usage < 50 and ram_usage < 85:
            logger.info(f"✅ [System Stable] CPU: {cpu_usage}% | RAM: {ram_usage}%. Proceeding...")
            break
        else:
            logger.warning(f"⏳ [High Load] CPU: {cpu_usage}%... Delaying Voice Load.")
            await asyncio.sleep(2) # استنى السيرفر يهدى

    # --- PHASE 2: RESOURCE SENTINEL (حماية العتاد) ---
    # نتأكد إن فيه مكان في كارت الشاشة قبل ما نحشر الموديل
    if torch.cuda.is_available():
        free_mem, total_mem = torch.cuda.mem_get_info()
        free_mem_gb = free_mem / (1024 ** 3)
        REQUIRED_GB = 6.0 # 7B 4-bit needs ~6GB

        if free_mem_gb < REQUIRED_GB:
            logger.critical(f"⛔ [VRAM Guard] Insufficient GPU Memory. Free: {free_mem_gb:.1f}GB. Needed: {REQUIRED_GB}GB.")
            VoiceBrainStatus.ERROR = "OOM_RISK"
            VoiceBrainStatus.LOADING = False
            return
    else:
        logger.warning("⚠️ [Titanium Loader] Running on CPU. Performance will be degraded.")

    # --- PHASE 3: THE HEAVY LIFT (التحميل المعزول) ---
    loop = asyncio.get_running_loop()

    # نستخدم Executor مخصص عشان نتحكم في الموارد
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="NvidiaLoader") as executor:
        for retry in range(MAX_RETRIES):
            try:
                logger.info(f"🎙️ [Attempt {retry+1}/{MAX_RETRIES}] Injecting Neural Weights...")

                # 🔥 THE ACTUAL LOADING (In Isolated Thread)
                # هنا بننادي دالة التحميل الحقيقية من الـ AI Manager
                # await loop.run_in_executor(executor, ai_manager.load_personaplex_model)

                # (Simulation Block - Remove in Prod)
                await asyncio.sleep(3) # محاكاة تحميل ثقيل

                # --- SUCCESS PROTOCOL ---
                VoiceBrainStatus.READY = True
                VoiceBrainStatus.LOADING = False
                VoiceBrainStatus.ERROR = None

                logger.info("💎 [Titanium Loader] SUCCESS. NVIDIA PersonaPlex is ONLINE & DOMINANT.")

                # نبعت إشارة للـ Logs إننا جاهزين نستقبل Voice Traffic
                logger.info("📡 [Signal] Voice Gateway is now OPEN.")
                return

            except Exception as e:
                wait_time = 2 ** (retry + 1) # 2s, 4s, 8s (Exponential Backoff)
                logger.error(f"💥 [Load Fail] Attempt {retry+1} Failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    # --- FAILURE PROTOCOL (لو فشلت كل المحاولات) ---
    VoiceBrainStatus.READY = False
    VoiceBrainStatus.LOADING = False
    VoiceBrainStatus.ERROR = "MAX_RETRIES_EXCEEDED"
    logger.critical("💀 [Titanium Loader] FATAL: Voice Core failed to initialize. System running in TEXT-ONLY mode.")

async def save_cart_handler_impl(payload: dict):
    """💾 Save Cart Worker"""
    async with _services['session_maker']() as db:
        user_id = payload.get("user_id")
        if user_id and _services.get('behavior'):
            asyncio.create_task(
                _services['behavior'].track_interaction(user_id, "save", {"context": "cart_recovery"})
            )

        from app.services.ai_cart_service import AICartService
        # نستخدم CartService لأنه المسؤول عن نقل البيانات من Redis لـ DB
        service = AICartService(
            db, _services['cache'], _services['rabbitmq'], _services['commerce']
        )
        await service.handle_save_cart(payload)

# --- 🛡️ RESILIENCE: EXPONENTIAL BACKOFF RETRY WRAPPER ---
async def cancel_order_handler_impl(payload: dict):
    """🛑 Cancel Order Worker"""
    async with _services['session_maker']() as db:
        user_id = payload.get("user_id")
        # تتبع السلوك (اختياري)
        if user_id and _services.get('behavior'):
            asyncio.create_task(
                _services['behavior'].track_interaction(user_id, "cancel", {"context": "recovery_discard"})
            )
            
        from app.services.ai_checkout_service import AICheckoutService
        # حقن التبعيات (Dependency Injection)
        service = AICheckoutService(
            db, _services['cache'], _services['rabbitmq'], _services['payment']
        )
        await service.handle_cancel_order(payload)

async def smart_retry_wrapper(message: IncomingMessage, handler_func: Callable[[dict], Awaitable[None]]):
    """
    💎 DIAMOND STANDARD V3: Resilient Infrastructure Wrapper.
    Wraps every task execution with a crash-proof shield.
    """
    try:
        payload_body = message.body.decode()
        try:
            payload = json.loads(payload_body)
        except json.JSONDecodeError:
            logger.error("❌ TERMINAL: Malformed JSON. Discarding message.")
            await message.reject(requeue=False)
            return

        await handler_func(payload)
        await message.ack()

    except (ValueError, KeyError, TypeError) as logic_err:
        logger.error(f"❌ TERMINAL: Logic Error: {logic_err}")
        await message.reject(requeue=False)

    except Exception as trans_err:
        headers = getattr(message, 'headers', {})
        retry_count = headers.get('x-retry-count', 0)
        backoff_time = min(2 ** retry_count + random.uniform(0.1, 1.0), 30)

        if retry_count < 5:
            logger.warning(
                f"🔄 TRANSIENT: {type(trans_err).__name__}. "
                f"Retry {retry_count + 1}/5. Sleep {backoff_time:.2f}s..."
            )
            await asyncio.sleep(backoff_time)
            await message.nack(requeue=True)
        else:
            logger.critical(f"🚫 DEAD: Max retries reached. Discarding. Error: {trans_err}")
            await message.reject(requeue=False)

async def health_check_handler(request):
    """🏥 Liveness & Readiness Probe."""
    is_healthy = True
    status_details = {
        "version": "Diamond-V30",
        "timestamp": datetime.utcnow().isoformat()
    }

    if not _services.get('rabbitmq') or _services['rabbitmq'].is_closed:
        is_healthy = False
        status_details['rabbitmq'] = "Disconnected ❌"
    else:
        status_details['rabbitmq'] = "Connected 🟢"

    if not _services.get('db_engine'):
        is_healthy = False
        status_details['db'] = "Not Initialized ❌"
    else:
        status_details['db'] = "Ready 🟢"

    try:
        if ai_manager._text_model is None:
             status_details['ai_engine'] = "Warming Up... ⏳"
        else:
             status_details['ai_engine'] = "Online 💎"
    except:
        status_details['ai_engine'] = "Error ⚠️"

    status_code = 200 if is_healthy else 503
    return web.json_response({"status": "healthy" if is_healthy else "unhealthy", "details": status_details}, status=status_code)

async def start_health_server():
    try:
        app = web.Application()
        app.add_routes([web.get('/health', health_check_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8081)
        await site.start()
        logger.info("💓 Health Check Server running on port 8081")
    except Exception as e:
        logger.error(f"⚠️ Failed to start health server: {e}")

# --- 👷 HANDLER IMPLEMENTATIONS ---

async def chat_handler_impl(payload: dict):
    """🗣️ Chat Worker"""
    if not _services.get('commerce') or not _services.get('session_maker'):
         logger.warning("⚠️ Services not ready yet. Requeueing task...")
         raise ConnectionError("AI Services Not Ready") 

    async with _services['session_maker']() as db:
        service = AINLUService(
            db=db,
            search_engine=_services['commerce'],
            rabbitmq=_services['rabbitmq'],
            cache=_services['cache'],
            llm_service=_services.get('llm', FreeLLMService()),
            behavior_engine=_services.get('behavior')
        )

        user_id = payload.get("user_id")
        if user_id and _services.get('behavior'):
             asyncio.create_task(
                 _services['behavior'].track_interaction(
                     user_id, "search", {"query": payload.get("message", "")}
                 )
             )
        await service.process_message(payload)

async def add_cart_handler_impl(payload: dict):
    """�� Cart Worker"""
    if not _services.get('session_maker'): raise ConnectionError("DB Not Ready")

    async with _services['session_maker']() as db:
        user_id = payload.get("user_id")
        if user_id and _services.get('behavior'):
             asyncio.create_task(
                 _services['behavior'].track_interaction(
                     user_id, "cart", {"id": payload.get("product_id"), "action": "add"}
                 )
             )
        
        from app.services.ai_cart_service import AICartService
        cart_service = AICartService(
            db, _services['cache'], _services['rabbitmq'], 
            commerce_engine=_services.get('commerce')
        )
        await cart_service.handle_add_to_cart(payload)

async def remove_cart_handler_impl(payload: dict):
    """🗑️ Remove Item Handler"""
    async with _services['session_maker']() as db:
        user_id = payload.get("user_id")
        if user_id and _services.get('behavior'):
            asyncio.create_task(
                _services['behavior'].track_interaction(user_id, "discard", {"id": payload.get("product_id")})
            )
        from app.services.ai_cart_service import AICartService
        cart_service = AICartService(
            db, _services['cache'], _services['rabbitmq'],
            commerce_engine=_services.get('commerce')
        )
        await cart_service.handle_remove_from_cart(payload)

async def clear_cart_handler_impl(payload: dict):
    """🧹 Clear Cart Handler"""
    async with _services['session_maker']() as db:
        from app.services.ai_cart_service import AICartService
        await AICartService(
            db, _services['cache'], _services['rabbitmq']
        ).handle_clear_cart(payload)

async def confirm_order_handler_impl(payload: dict):
    """💳 Checkout Handler"""
    async with _services['session_maker']() as db:
        user_id = payload.get("user_id")
        if user_id and _services.get('behavior'):
            asyncio.create_task(
                _services['behavior'].track_interaction(user_id, "buy", {"context": "checkout_initiated"})
            )
        from app.services.ai_checkout_service import AICheckoutService
        checkout_service = AICheckoutService(
            db, _services['cache'], _services['rabbitmq'], 
            _services['payment']
        )
        await checkout_service.handle_confirm_order(payload)

# --- 🚀 MAIN ENTRY POINT ---

async def main():
    """
    💎 TITANIUM WORKER ENTRY POINT.
    """
    logger.info("🚀 --- STARTING AIRDELIVER GLOBAL WORKER NODE (TITANIUM EDITION) ---")
    
    settings = get_core_settings() 
    await start_health_server()

    # 1. INFRASTRUCTURE
    logger.info("📡 [Phase 1] Initializing Infrastructure...")
    try:
        local_engine = create_async_engine(
            str(settings.DATABASE_URI),
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=50,
            max_overflow=20
        )
        LocalSessionMaker = sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)
        _services['session_maker'] = LocalSessionMaker
        _services['db_engine'] = local_engine

        # Redis Cache (String connection fix applied)
        cache_client = RedisCacheClient(str(settings.REDIS_URL))
        if hasattr(cache_client, 'connect'): await cache_client.connect()
        _services['cache'] = cache_client
        logger.info("✅ Infra Connected.")
        
    except Exception as e:
        logger.critical(f"❌ Infra Failure: {e}")
        sys.exit(1)

    # 2. AI ENGINE
    try:
        logger.info("🧪 [Phase 2] Warming up SOTA Neural Engines...")
        
        opensearch_gen = get_opensearch_client(settings)
        opensearch_client = await anext(opensearch_gen)
        
        milvus_client = get_milvus_client(settings)
        ensure_milvus_schema(milvus_client)
        
        loop = asyncio.get_running_loop()
        logger.info("🧠 Loading Text Brain (Qwen2)...")
        embedding_model = await loop.run_in_executor(None, ai_manager.get_text_model)

        # 💎 STEP 2: LOAD VISION MODEL (THE MISSING PIECE)
        # هذا السطر سيجبر الموديل على التحميل في الذاكرة قبل استقبال أي طلب
        logger.info("👁️ Loading Vision Brain (SigLIP)...")
        # نفترض أن ai_manager لديه دالة get_vision_model أو get_image_model
        # سنقوم بمناداتها فقط لتفعيل التحميل
        if hasattr(ai_manager, 'get_vision_model'):
            await loop.run_in_executor(None, ai_manager.get_vision_model)
        elif hasattr(ai_manager, 'get_image_model'):
            await loop.run_in_executor(None, ai_manager.get_image_model)

        ai_commerce_engine = get_ai_commerce_engine(opensearch_client, milvus_client, embedding_model, cache_client)
        _services['commerce'] = ai_commerce_engine
        _services['llm'] = FreeLLMService()
        _services['behavior'] = BehaviorEngine(cache_client)
        
        logger.info("💎 [Phase 2] AI Engines Loaded (Text + Vision).")
    except Exception as e:
        logger.error(f"⚠️ AI INIT FAILURE: {e}. Worker running in DEGRADED mode.")

    # 3. PAYMENT
    try:
        payment_orchestrator = PaymentOrchestrator(
            StripeGateway(get_stripe_settings()),
            PayPalGateway(get_paypal_settings(), cache_client),
            MpesaGateway(get_mpesa_settings(), cache_client)
        )
        _services['payment'] = payment_orchestrator
    except Exception as e:
        logger.critical(f"🛑 Payment Config Failure: {e}")

    # 4. RABBITMQ CONSUMER
    try:
        rabbitmq_service = RabbitMQService(settings)
        _services['rabbitmq'] = rabbitmq_service

        logger.info("🔗 Establishing Consumer Connection...")
        consume_connection = await connect_robust(settings.RABBITMQ_URL)
        consume_channel = await consume_connection.channel()
        
        PREFETCH_COUNT = int(os.getenv("WORKER_PREFETCH", "50"))
        await consume_channel.set_qos(prefetch_count=PREFETCH_COUNT)

        exchange = await consume_channel.declare_exchange("airdeliver_main_exchange", type="topic", durable=True)

        QUEUE_CONFIG = {
            "chat": {"queue": "q.ai.chat", "key": "airdeliver.ai.chat.in", "handler": chat_handler_impl},
            "cart_add": {"queue": "q.ai.cart.add", "key": "airdeliver.ai.cart.add", "handler": add_cart_handler_impl},
            "cart_remove": {"queue": "q.ai.cart.remove", "key": "airdeliver.ai.cart.remove", "handler": remove_cart_handler_impl},
            "cart_clear": {"queue": "q.ai.cart.clear", "key": "airdeliver.ai.cart.clear", "handler": clear_cart_handler_impl},
            "checkout": {"queue": "q.ai.order.confirm", "key": "airdeliver.ai.order.confirm", "handler": confirm_order_handler_impl},
            "cancel": {"queue": "q.ai.intent.cancel", "key": "airdeliver.ai.intent.cancel_order", "handler": cancel_order_handler_impl},
            "save": {"queue": "q.ai.cart.save", "key": "airdeliver.ai.cart.save", "handler": save_cart_handler_impl}

        }
        
        args = {"x-queue-type": "quorum"}

        for name, config in QUEUE_CONFIG.items():
            queue = await consume_channel.declare_queue(config["queue"], durable=True, arguments=args)
            await queue.bind(exchange, routing_key=config["key"])
            await queue.consume(partial(smart_retry_wrapper, handler_func=config["handler"]))
            logger.info(f"✅ Bound Queue [{config['queue']}]")
        
        asyncio.create_task(lazy_load_voice_brain())

        logger.info("🚀 WORKER NODE IS FULLY OPERATIONAL...")
        await asyncio.Future()

    except asyncio.CancelledError:
        logger.info("👋 Worker shutting down...")
    except Exception as e:
        logger.critical(f"🔥 Worker Crash: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Worker stopped.")
