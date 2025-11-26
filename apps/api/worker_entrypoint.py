# apps/api/worker_entrypoint.py

import asyncio
import json
import logging
import os
import signal
from aio_pika.abc import AbstractIncomingMessage

# Core Configuration
from app.core.config import (
    get_core_settings, CoreSettings,
    get_stripe_settings, get_paypal_settings, get_mpesa_settings
)
from app.db.session import SessionLocal

# Services
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import RedisCacheClient, IAsyncCacheClient, get_cache_client
from app.services.ai_nlu_service import AINLUService
from app.services.ai_cart_service import AICartService
from app.services.ai_checkout_service import AICheckoutService
from app.services.free_llm_service import FreeLLMService # The New AI Brain

# Payment
from app.services.payment_orchestrator import (
    PaymentOrchestrator, StripeGateway, PayPalGateway, MpesaGateway
)

# AI Engine
from app.services.ai_commerce_engine import (
    AICommerceEngine,
    get_ai_commerce_engine,
    get_opensearch_client,
    get_milvus_client,
    get_embedding_model
)

# Vector DB Drivers
from opensearchpy import AsyncOpenSearch
from pymilvus import MilvusClient, DataType
from sentence_transformers import SentenceTransformer

# Enterprise Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def ensure_milvus_schema(client: MilvusClient, collection_name: str = "airdeliver_products"):
    try:
        if client.has_collection(collection_name):
            logger.info(f"✅ Milvus Collection '{collection_name}' exists.")
        else:
            logger.warning(f"⚠️ Milvus Collection '{collection_name}' missing. Auto-creating with Explicit Schema...")
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True, description="airdeliver Products Vector Store")
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
            index_params = client.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="FLAT", metric_type="L2")
            client.create_collection(collection_name=collection_name, schema=schema, index_params=index_params)
            logger.info(f"✅ Milvus Collection '{collection_name}' created successfully with strict schema.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Milvus schema: {e}")

async def main():
    logger.info("🚀 --- Starting airdeliver Global Worker Service (AI Enhanced) ---")
    settings = get_core_settings()
    worker_type = os.environ.get("WORKER_TYPE", "AI")

    # 1. Initialize Infrastructure
    rabbitmq = await get_rabbitmq_service(settings)
    cache_client = RedisCacheClient(url=settings.REDIS_URL)
    await cache_client.connect()
    logger.info("✅ Redis Cache Connected.")

    app_dependencies = {
        "settings": settings,
        "rabbitmq": rabbitmq,
        "cache": cache_client,
    }

    opensearch_client = None
    queues_bindings = {}

    if worker_type == "AI":
        logger.info("🧠 Initializing AI Commerce Cortex...")
        
        # 2. Setup Vector Search Engines
        opensearch_client_gen = get_opensearch_client(settings)
        opensearch_client = await anext(opensearch_client_gen)
        milvus_client = get_milvus_client()
        ensure_milvus_schema(milvus_client)
        embedding_model = get_embedding_model()

        ai_commerce_engine = AICommerceEngine(opensearch_client, milvus_client, embedding_model, cache_client)
        logger.info("✅ AI RAG Engine Online.")
        app_dependencies["ai_engine"] = ai_commerce_engine

        # 3. Setup Generative AI Service (Llama 3)
        free_llm_service = FreeLLMService()
        logger.info("🤖 FreeLLMService (Groq/Llama3) Initialized.")

        # 4. Setup Payment Orchestration
        try:
            stripe_gw = StripeGateway(get_stripe_settings())
            paypal_gw = PayPalGateway(get_paypal_settings(), cache_client)
            mpesa_gw = MpesaGateway(get_mpesa_settings(), cache_client)
            payment_orchestrator = PaymentOrchestrator(stripe_gw, paypal_gw, mpesa_gw)
            app_dependencies["payment_orchestrator"] = payment_orchestrator
        except Exception as e:
            logger.critical(f"🔥 Payment System Init Failed: {e}", exc_info=True)
            return

        # 5. Message Handlers
        async def handle_chat_message(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    # Injecting FreeLLMService into AINLUService
                    nlu_service = AINLUService(
                        db, 
                        app_dependencies["ai_engine"], 
                        rabbitmq, 
                        cache_client,
                        free_llm_service 
                    )
                    await nlu_service.process_message(payload)

        async def handle_add_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    cart_service = AICartService(db, cache_client, rabbitmq)
                    await cart_service.handle_add_to_cart(payload)

        async def handle_remove_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    cart_service = AICartService(db, cache_client, rabbitmq)
                    await cart_service.handle_remove_from_cart(payload)

        async def handle_removal_recovery(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    # Injecting FreeLLMService here too for smarter recovery suggestions
                    nlu_service = AINLUService(
                        db, 
                        app_dependencies["ai_engine"], 
                        rabbitmq, 
                        cache_client,
                        free_llm_service
                    )
                    await nlu_service.process_removal_recovery(payload)

        async def handle_clear_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    cart_service = AICartService(db, cache_client, rabbitmq)
                    await cart_service.handle_clear_cart(payload)

        async def handle_confirm_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    checkout_service = AICheckoutService(db, cache_client, rabbitmq, app_dependencies["payment_orchestrator"])
                    await checkout_service.handle_confirm_order(payload)

        async def handle_cancel_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                async with SessionLocal() as db:
                    checkout_service = AICheckoutService(db, cache_client, rabbitmq, app_dependencies["payment_orchestrator"])
                    await checkout_service.handle_cancel_order(payload)

        # 6. Queue Bindings
        queues_bindings.update({
            "q.ai.chat": ("airdeliver.ai.chat.in", handle_chat_message),
            "q.ai.intent.add": ("airdeliver.ai.intent.add_to_cart", handle_add_intent),
            "q.ai.intent.remove": ("airdeliver.ai.intent.remove_from_cart", handle_remove_intent),
            "q.ai.intent.recovery": ("airdeliver.ai.intent.removal_recovery", handle_removal_recovery),
            "q.ai.intent.clear": ("airdeliver.ai.intent.clear_cart", handle_clear_intent),
            "q.ai.intent.confirm": ("airdeliver.ai.intent.confirm_order", handle_confirm_intent),
            "q.ai.intent.cancel": ("airdeliver.ai.intent.cancel_order", handle_cancel_intent),
        })

    # 7. Start Consumers
    consume_tasks = []
    for q_name, (binding_key, handler) in queues_bindings.items():
        queue = await rabbitmq.channel.declare_queue(q_name, durable=True)
        await queue.bind(rabbitmq.exchange_name, routing_key=binding_key)
        await rabbitmq.channel.set_qos(prefetch_count=10)
        task = asyncio.create_task(queue.consume(handler))
        consume_tasks.append(task)
        logger.info(f"🎧 Consumer started: {q_name} -> {binding_key}")

    logger.info(f"✅ airdeliver {worker_type} Worker is operational.")

    # 8. Graceful Shutdown Logic
    stop_event = asyncio.Event()
    def handle_stop_signal():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_stop_signal)

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("🛑 Shutting down worker...")
        for task in consume_tasks: task.cancel()
        await asyncio.gather(*consume_tasks, return_exceptions=True)
        if opensearch_client: await opensearch_client.close()
        await rabbitmq.close()
        await cache_client.disconnect()
        logger.info("👋 Worker shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
