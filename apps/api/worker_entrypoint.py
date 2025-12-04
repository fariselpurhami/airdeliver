# apps/api/worker_entrypoint.py

import asyncio
import json
import logging
import signal
import decimal
import datetime
import uvloop 
import os
from pathlib import Path
from typing import Any

# --- 🛠️ ARCHITECT'S FORCE LOAD (THE FIX) ---
from dotenv import load_dotenv

# 1. Locate the .env file relative to THIS script
current_dir = Path(__file__).resolve().parent
env_path = current_dir / ".env"

# 2. Force load it (Override system vars if needed)
load_result = load_dotenv(dotenv_path=env_path, override=True)

# 3. Diagnostic Report (Read this in logs!)
print("\n" + "="*50)
print(f"🕵️‍♂️ ARCHITECT DIAGNOSTIC PROBE:")
print(f"📍 Script Location: {current_dir}")
print(f"📄 Looking for .env at: {env_path}")
print(f"✅ File Exists? {env_path.exists()}")
print(f"📥 Loaded .env? {load_result}")
key_status = os.getenv("GROQ_API_KEY")
print(f"🔑 GROQ_API_KEY Status: {'✅ FOUND' if key_status else '❌ MISSING'}")
if key_status:
    print(f"👀 Key Preview: {key_status[:5]}......")
print("="*50 + "\n")
# ---------------------------------------------

from aio_pika.abc import AbstractIncomingMessage
from app.core.config import get_core_settings
from app.db.session import SessionLocal, engine 
from app.services.rabbitmq_service import get_rabbitmq_service
from app.services.cache_service import RedisCacheClient
from app.services.ai_nlu_service import AINLUService
from app.services.ai_cart_service import AICartService
from app.services.ai_checkout_service import AICheckoutService
from app.services.free_llm_service import FreeLLMService
from app.services.ai_commerce_engine import (
    get_ai_commerce_engine,
    get_opensearch_client,
    get_milvus_client,
    get_embedding_model
)
from pymilvus import MilvusClient, DataType
from sqlalchemy.ext.asyncio import create_async_engine 
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# --- SAFE JSON ENCODER ---
class SafeJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode='json')
        if hasattr(obj, "dict"):
            return obj.dict()
        return str(obj)

_original_dumps = json.dumps
def safe_dumps(*args, **kwargs):
    kwargs['cls'] = SafeJSONEncoder
    return _original_dumps(*args, **kwargs)
json.dumps = safe_dumps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("airdeliver.worker")

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def ensure_milvus_schema(client: MilvusClient, collection_name: str = "airdeliver_products"):
    try:
        if not client.has_collection(collection_name):
            logger.warning(f"⚠️ Infrastructure: Auto-healing Milvus Collection '{collection_name}'...")
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
            index_params = client.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="FLAT", metric_type="L2")
            client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)
            logger.info("✅ Milvus Schema Restored.")
    except Exception as e:
        logger.error(f"❌ Milvus Init Error: {e}")

async def main():
    logger.info("🚀 --- STARTING AIRDELIVER GLOBAL WORKER NODE (v15.0 - ENV ENFORCER) ---")
    
    settings = get_core_settings()
    
    # --- 💉 INTELLIGENT NETWORK OVERRIDES ---
    
    # 1. RabbitMQ
    if settings.RABBITMQ_HOST == "mq":
        settings.RABBITMQ_HOST = "localhost"
    
    # 2. Redis
    final_redis_url = settings.REDIS_URL
    if "redis:6379" in final_redis_url:
        final_redis_url = final_redis_url.replace("redis:6379", "localhost:6379")

    # 3. OpenSearch
    if settings.OPENSEARCH_HOST == "opensearch":
         settings.OPENSEARCH_HOST = "localhost"

    # 4. Milvus
    final_milvus_uri = settings.MILVUS_URI
    if "milvus:19530" in final_milvus_uri:
         final_milvus_uri = final_milvus_uri.replace("milvus:19530", "localhost:19530")

    # 5. Database
    final_db_uri = str(settings.DATABASE_URI)
    if "@postgres:" in final_db_uri:
        logger.warning("🌐 HYBRID MODE: Patching Database URI to 'localhost'...")
        final_db_uri = final_db_uri.replace("@postgres:", "@localhost:")
    
    local_engine = create_async_engine(final_db_uri, echo=False, future=True)
    LocalSessionMaker = sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)

    logger.info("✅ ALL NETWORK PATCHES APPLIED.")
    # ----------------------------------------

    rabbitmq = await get_rabbitmq_service(settings)
    
    cache_client = RedisCacheClient(url=final_redis_url)
    await cache_client.connect()
    logger.info("✅ Redis: Connected")

    opensearch_gen = get_opensearch_client(settings)
    opensearch_client = await anext(opensearch_gen)
    
    milvus_client = MilvusClient(uri=final_milvus_uri)
    ensure_milvus_schema(milvus_client)
    
    embedding_model = get_embedding_model() 

    ai_commerce_engine = get_ai_commerce_engine(opensearch_client, milvus_client, embedding_model)
    await ai_commerce_engine.ensure_opensearch_index()
    logger.info("✅ RAG Engine: Online")

    try:
        free_llm_service = FreeLLMService()
        if not free_llm_service.client:
            logger.warning("⚠️ WARNING: GROQ_API_KEY missing.")
        else:
            logger.info("🧠 Cognitive Brain: Online")
    except Exception as e:
        logger.critical(f"❌ LLM Init Failed: {e}")

    async def robust_wrapper(message: AbstractIncomingMessage, handler_func):
        async with message.process(): 
            try:
                payload = json.loads(message.body.decode())
                await handler_func(payload)
            except Exception as e:
                logger.error(f"💥 WORKER EXCEPTION in {handler_func.__name__}: {e}", exc_info=True)
                try:
                    raw = json.loads(message.body.decode())
                    user_id = raw.get("user_id")
                    if user_id:
                        await rabbitmq.publish(
                            {"user_id": user_id, "content": "Thinking process interrupted. Retry?", "type": "error"},
                            "airdeliver.ai.response.out"
                        )
                except: pass 

    async def chat_handler(payload):
        async with LocalSessionMaker() as db:
            service = AINLUService(db, ai_commerce_engine, rabbitmq, cache_client, free_llm_service)
            await service.process_message(payload)

    async def add_cart_handler(payload):
        async with LocalSessionMaker() as db:
            await AICartService(db, cache_client, rabbitmq).handle_add_to_cart(payload)

    async def remove_cart_handler(payload):
        async with LocalSessionMaker() as db:
            await AICartService(db, cache_client, rabbitmq).handle_remove_from_cart(payload)

    async def clear_cart_handler(payload):
        async with LocalSessionMaker() as db:
            await AICartService(db, cache_client, rabbitmq).handle_clear_cart(payload)

    await rabbitmq.channel.set_qos(prefetch_count=10)

    queues = {
        "q.ai.chat": ("airdeliver.ai.chat.in", chat_handler),
        "q.ai.intent.add": ("airdeliver.ai.intent.add_to_cart", add_cart_handler),
        "q.ai.intent.remove": ("airdeliver.ai.intent.remove_from_cart", remove_cart_handler),
        "q.ai.intent.clear": ("airdeliver.ai.intent.clear_cart", clear_cart_handler),
    }

    for q_name, (key, func) in queues.items():
        queue = await rabbitmq.channel.declare_queue(q_name, durable=True)
        await queue.bind(rabbitmq.exchange_name, routing_key=key)
        await queue.consume(lambda m, f=func: robust_wrapper(m, f))
        logger.info(f"🎧 Bound Consumer: {q_name} -> {key}")

    logger.info("✅ WORKER READY. Waiting for traffic...")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    
    if opensearch_client: await opensearch_client.close()
    await rabbitmq.close()
    await cache_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
