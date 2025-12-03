# apps/api/worker_entrypoint.py

import asyncio
import json
import logging
import os
import signal
import uvloop 
from aio_pika.abc import AbstractIncomingMessage
from app.core.config import (
    get_core_settings, 
    get_stripe_settings, get_paypal_settings, get_mpesa_settings
)
from app.db.session import SessionLocal
from app.services.rabbitmq_service import get_rabbitmq_service
from app.services.cache_service import RedisCacheClient
from app.services.ai_nlu_service import AINLUService
from app.services.ai_cart_service import AICartService
from app.services.ai_checkout_service import AICheckoutService
from app.services.free_llm_service import FreeLLMService
from app.services.payment_orchestrator import (
    PaymentOrchestrator, StripeGateway, PayPalGateway, MpesaGateway
)
from app.services.ai_commerce_engine import (
    get_ai_commerce_engine,
    get_opensearch_client,
    get_milvus_client,
    get_embedding_model
)
from pymilvus import MilvusClient, DataType

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
    logger.info("🚀 --- STARTING AIRDELIVER GLOBAL WORKER NODE (v5.0) ---")
    settings = get_core_settings()
    
    rabbitmq = await get_rabbitmq_service(settings)
    cache_client = RedisCacheClient(url=settings.REDIS_URL)
    await cache_client.connect()

    logger.info("✅ Redis: Connected (High-Speed Cache Layer)")
    logger.info("🧠 Loading Neural Commerce Engines...")
    
    opensearch_gen = get_opensearch_client(settings)
    opensearch_client = await anext(opensearch_gen)
    
    milvus_client = get_milvus_client(settings) 
    ensure_milvus_schema(milvus_client)
    embedding_model = get_embedding_model() 

    ai_commerce_engine = get_ai_commerce_engine(opensearch_client, milvus_client, embedding_model)
    await ai_commerce_engine.ensure_opensearch_index()
    logger.info("✅ RAG Engine: Online & Indexed")

    free_llm_service = FreeLLMService()
    logger.info("🤖 LLM Core: Online (Polyglot Enabled)")

    try:
        payment_orchestrator = PaymentOrchestrator(
            StripeGateway(get_stripe_settings()),
            PayPalGateway(get_paypal_settings(), cache_client),
            MpesaGateway(get_mpesa_settings(), cache_client)
        )
    except Exception as e:
        logger.critical(f"🔥 Payment System Failure: {e}")
        return

    async def robust_wrapper(message: AbstractIncomingMessage, handler_func):
        """
        🛡️ INFRASTRUCTURE SHIELD:
        Ensures that NO error crashes the worker or leaves the UI hanging.
        """
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
                        err_msg = "⚠️ System hiccup. I'm rebooting my thought process. Please try again."
                        await rabbitmq.publish(
                            {"user_id": user_id, "content": err_msg, "type": "error"},
                            "airdeliver.ai.response.out"
                        )
                except:
                    pass 

    async def chat_handler(payload):
        async with SessionLocal() as db:
            service = AINLUService(db, ai_commerce_engine, rabbitmq, cache_client, free_llm_service)
            await service.process_message(payload)

    async def add_cart_handler(payload):
        async with SessionLocal() as db:
            await AICartService(db, cache_client, rabbitmq).handle_add_to_cart(payload)

    async def remove_cart_handler(payload):
        async with SessionLocal() as db:
            await AICartService(db, cache_client, rabbitmq).handle_remove_from_cart(payload)

    async def clear_cart_handler(payload):
        async with SessionLocal() as db:
            await AICartService(db, cache_client, rabbitmq).handle_clear_cart(payload)

    async def confirm_order_handler(payload):
        async with SessionLocal() as db:
            await AICheckoutService(db, cache_client, rabbitmq, payment_orchestrator).handle_confirm_order(payload)

    await rabbitmq.channel.set_qos(prefetch_count=10)

    queues = {
        "q.ai.chat": ("airdeliver.ai.chat.in", chat_handler),
        "q.ai.intent.add": ("airdeliver.ai.intent.add_to_cart", add_cart_handler),
        "q.ai.intent.remove": ("airdeliver.ai.intent.remove_from_cart", remove_cart_handler),
        "q.ai.intent.clear": ("airdeliver.ai.intent.clear_cart", clear_cart_handler),
        "q.ai.intent.confirm": ("airdeliver.ai.intent.confirm_order", confirm_order_handler),
    }

    for q_name, (key, func) in queues.items():
        queue = await rabbitmq.channel.declare_queue(q_name, durable=True)
        await queue.bind(rabbitmq.exchange_name, routing_key=key)
        
        await queue.consume(lambda m, f=func: robust_wrapper(m, f))
        logger.info(f"🎧 Bound Consumer: {q_name} -> {key}")

    logger.info("✅ WORKER FULLY OPERATIONAL. Waiting for events...")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    
    logger.info("🛑 Shutting down infrastructure...")
    if opensearch_client: await opensearch_client.close()
    await rabbitmq.close()
    await cache_client.disconnect()
    logger.info("👋 Goodnight.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
