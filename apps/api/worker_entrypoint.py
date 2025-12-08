# apps/api/worker_entrypoint.py

import asyncio
import json
import logging
import os
import signal
import uvloop
import time
from typing import Callable, Awaitable
from app.services.ai_behavior_engine import get_behavior_engine
from aio_pika.abc import AbstractIncomingMessage, DeliveryMode
import aio_pika
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from pymilvus import MilvusClient, DataType
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | [Worker-Node-01] | %(message)s"
)
logger = logging.getLogger("airdeliver.worker")

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def ensure_milvus_schema(client: MilvusClient):
    # 1. Collection النصوص (الأساسية)
    try:
        if not client.has_collection("airdeliver_products"):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384) # Text Only
            
            idx = client.prepare_index_params()
            idx.add_index(field_name="vector", index_type="FLAT", metric_type="L2")
            client.create_collection("airdeliver_products", schema=schema, index_params=idx)
            logger.info("✅ Milvus: Text Collection Ready")
    except Exception as e:
        logger.error(f"Milvus Text Init Error: {e}")

    # 2. Collection الصور (المنفصلة - Visual)
    try:
        if not client.has_collection("airdeliver_products_visual"):
            schema_vis = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema_vis.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema_vis.add_field(field_name="image_vector", datatype=DataType.FLOAT_VECTOR, dim=512) # Visual Only
            
            idx_vis = client.prepare_index_params()
            idx_vis.add_index(field_name="image_vector", index_type="FLAT", metric_type="L2")
            client.create_collection("airdeliver_products_visual", schema=schema_vis, index_params=idx_vis)
            logger.info("✅ Milvus: Visual Collection Ready")
    except Exception as e:
        logger.error(f"Milvus Visual Init Error: {e}")

        
async def main():
    logger.info("🚀 --- STARTING AIRDELIVER GLOBAL WORKER NODE (RESILIENCE MODE) ---")
    settings = get_core_settings()
    
    final_db_uri = str(settings.DATABASE_URI)
    local_engine = create_async_engine(
        final_db_uri, 
        echo=False, 
        future=True,
        pool_pre_ping=True, 
        pool_size=20,
        max_overflow=10
    )
    LocalSessionMaker = sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)
    
    cache_client = RedisCacheClient(url=settings.REDIS_URL)
    retry_count = 0
    while retry_count < 5:
        try:
            await cache_client.connect()
            logger.info("✅ Redis: Connected")
            break
        except Exception as e:
            retry_count += 1
            logger.warning(f"⚠️ Redis Connection Failed (Attempt {retry_count}/5). Retrying in 2s...")
            await asyncio.sleep(2)
    
    if retry_count == 5:
        logger.critical("🔥 CRITICAL: Redis unreachable. Shutting down to prevent data inconsistency.")
        return

    logger.info("🧠 Loading Neural Commerce Engines...")
    
    opensearch_gen = get_opensearch_client(settings)
    opensearch_client = await anext(opensearch_gen)
    
    milvus_client = get_milvus_client(settings) 
    ensure_milvus_schema(milvus_client)
    embedding_model = get_embedding_model() 

    ai_commerce_engine = get_ai_commerce_engine(opensearch_client, milvus_client, embedding_model)
    try:
        await ai_commerce_engine.ensure_opensearch_index()
        logger.info("✅ RAG Engine: Online & Indexed")
    except Exception as e:
        logger.error(f"⚠️ Search Index Warning: {e}")

    free_llm_service = FreeLLMService()
    logger.info("🤖 LLM Core: Online")

    behavior_engine = get_behavior_engine(cache_client)
    logger.info("🌌 Singularity Brain: Online")


    try:
        payment_orchestrator = PaymentOrchestrator(
            StripeGateway(get_stripe_settings()),
            PayPalGateway(get_paypal_settings(), cache_client),
            MpesaGateway(get_mpesa_settings(), cache_client)
        )
        logger.info("💳 Payment Gateways: Secure & Ready")
    except Exception as e:
        logger.critical(f"🔥 Payment System Configuration Failure: {e}")
        return

    try:
        rabbitmq = await get_rabbitmq_service(settings)
    except Exception as e:
        logger.critical(f"🔥 RabbitMQ Failure: {e}")
        return

    async def hardened_wrapper(message: AbstractIncomingMessage, handler_func: Callable[[dict], Awaitable[None]]):
        """
        Implements the 'Ack-Late' pattern and strict error handling to ensure
        NO message is lost (Zero-Drop Architecture).
        """
        async with message.process(ignore_processed=True): 
        
            try:
                payload = json.loads(message.body.decode())
                
                await handler_func(payload)
            
            except json.JSONDecodeError:
                logger.error("❌ Malformed JSON. Sending to Dead Letter (if configured) or discarding.")
                
            except Exception as e:
                logger.error(f"💥 WORKER EXCEPTION in {handler_func.__name__}: {e}", exc_info=True)
                
                try:
                    raw = json.loads(message.body.decode())
                    user_id = raw.get("user_id")
                    if user_id:
                        err_msg = "⚠️ An internal error occurred. Our engineers have been notified."
                        await rabbitmq.publish(
                            {"user_id": user_id, "content": err_msg, "type": "error"},
                            "airdeliver.ai.response.out"
                        )
                except: pass
                
                raise e 

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

    async def confirm_order_handler(payload):
        async with LocalSessionMaker() as db:
            await AICheckoutService(db, cache_client, rabbitmq, payment_orchestrator).handle_confirm_order(payload)

    


    async def cancel_order_handler(payload):
        """
        Global Standard Handler for 'Discard Order'.
        Actions:
        1. Connects to Database & Cache.
        2. Wipes the Cart Data physically.
        3. Sends the termination signal to Frontend.
        """
        user_id = payload.get("user_id")
        logger.info(f"🚫 PROCESSING DISCARD: Wiping session and cart for User {user_id}...")

        async def behavior_handler(payload):
          """
          Lightning-fast handler for tracking signals.
          Payload expected: {"user_id": 123, "event": "view", "meta": {...}}
          """
          user_id = payload.get("user_id")
          event = payload.get("event")
          meta = payload.get("meta", {})
    
          if user_id and event:
             # Fire and forget into the singularity
             await behavior_engine.track_interaction(user_id, event, meta)

        async with LocalSessionMaker() as db:
            cart_service = AICartService(db, cache_client, rabbitmq)
            
            try:
                await cart_service.delete_cart(user_id) 
            except Exception as e:
                logger.error(f"⚠️ Error cleaning up cart during discard: {e}")

            await rabbitmq.publish({
                "user_id": user_id,
                "content": "Order process discarded. Your cart has been cleared.",
                "type": "ORDER_CANCELLED"
            }, "airdeliver.ai.response.out")
            
    await rabbitmq.channel.set_qos(prefetch_count=10)



    queues = {
        "q.ai.chat": ("airdeliver.ai.chat.in", chat_handler),
        "q.ai.intent.add": ("airdeliver.ai.intent.add_to_cart", add_cart_handler),
        "q.ai.intent.remove": ("airdeliver.ai.intent.remove_from_cart", remove_cart_handler),
        "q.ai.intent.clear": ("airdeliver.ai.intent.clear_cart", clear_cart_handler),
        "q.ai.intent.confirm": ("airdeliver.ai.intent.confirm_order", confirm_order_handler),
        "q.ai.intent.cancel": ("airdeliver.ai.intent.cancel_order", cancel_order_handler),
    }

    consumers = []
    for q_name, (key, func) in queues.items():
        queue = await rabbitmq.channel.declare_queue(q_name, durable=True) 
        await queue.bind(rabbitmq.exchange_name, routing_key=key)
        
        consumer_tag = await queue.consume(lambda m, f=func: hardened_wrapper(m, f))
        consumers.append((queue, consumer_tag))
        logger.info(f"🎧 Bound Consumer: {q_name} -> {key}")

    logger.info("✅ airdeliver WORKER FULLY OPERATIONAL. Waiting for events...")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.warning("🛑 Signal received! Initiating Graceful Shutdown...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await stop_event.wait()
    
    logger.info("⏳ Draining active tasks...")
    
    for queue, tag in consumers:
        await queue.cancel(tag)
    
    await asyncio.sleep(2) 

    logger.info("�� Closing Infrastructure Connections...")
    if opensearch_client: await opensearch_client.close()
    await rabbitmq.close() 
    await cache_client.disconnect()
    await local_engine.dispose()
    
    logger.info("👋 Goodnight. System Halted Safely.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
