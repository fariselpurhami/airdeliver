# apps/api/worker_entrypoint.py

import asyncio
import json
import logging
import os
from aio_pika.abc import AbstractIncomingMessage
from app.core.config import get_core_settings, CoreSettings
from app.db.session import SessionLocal
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import RedisCacheClient, IAsyncCacheClient, get_cache_client
from app.services.ai_nlu_service import AINLUService
from app.services.ai_cart_service import AICartService
from app.services.ai_checkout_service import AICheckoutService
from app.services.payment_orchestrator import (
    PaymentOrchestrator, StripeGateway, PayPalGateway, MpesaGateway
)

from app.services.ai_commerce_engine import (
    AICommerceEngine,
    get_ai_commerce_engine,
    get_opensearch_client,
    get_milvus_client,
    get_embedding_model
)
from app.services import telemetry_consumer, event_consumer
from opensearchpy import AsyncOpenSearch
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("--- Starting AirDeliver Worker Service ---")
    settings = get_core_settings()
    worker_type = os.environ.get("WORKER_TYPE", "AI")

    rabbitmq = await get_rabbitmq_service(settings)
    cache_client = RedisCacheClient(url=settings.REDIS_URL)
    await cache_client.connect()
    logger.info("Cache connected.")

    app_dependencies = {
        "settings": settings,
        "rabbitmq": rabbitmq,
        "cache": cache_client,
    }

    opensearch_client = None
    queues_bindings = {}

    if worker_type == "AI":
        logger.info(f"--- Initializing {worker_type} Worker Dependencies ---")

        logger.info("Initializing Hybrid Search Engine...")
        opensearch_client_gen = get_opensearch_client(settings)
        opensearch_client = await anext(opensearch_client_gen)
        milvus_client = get_milvus_client()
        embedding_model = get_embedding_model()
        ai_commerce_engine = AICommerceEngine(opensearch_client, milvus_client, embedding_model)
        logger.info("Hybrid Search Engine initialized.")
        app_dependencies["ai_engine"] = ai_commerce_engine

        stripe_gw = StripeGateway(settings)
        paypal_gw = PayPalGateway(settings, cache_client)
        mpesa_gw = MpesaGateway(settings, cache_client)
        payment_orchestrator = PaymentOrchestrator(stripe_gw, paypal_gw, mpesa_gw)
        logger.info("Payment Orchestrator initialized.")
        app_dependencies["payment_orchestrator"] = payment_orchestrator

        async def handle_chat_message(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                logger.info(f"Worker processing: chat.in for user {payload.get('user_id')}")
                async with SessionLocal() as db:
                    nlu_service = AINLUService(db, app_dependencies["ai_engine"], rabbitmq)
                    await nlu_service.process_message(payload)

        async def handle_add_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                logger.info(f"Worker processing: intent.add for user {payload.get('user_id')}")
                async with SessionLocal() as db:
                    cart_service = AICartService(db, cache_client, rabbitmq)
                    await cart_service.handle_add_to_cart(payload)

        async def handle_remove_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                logger.info(f"Worker processing: intent.remove for user {payload.get('user_id')}")
                async with SessionLocal() as db:
                    cart_service = AICartService(db, cache_client, rabbitmq)
                    await cart_service.handle_remove_from_cart(payload)

        async def handle_confirm_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                logger.info(f"Worker processing: intent.confirm for user {payload.get('user_id')}")
                async with SessionLocal() as db:
                    checkout_service = AICheckoutService(db, cache_client, rabbitmq, app_dependencies["payment_orchestrator"])
                    await checkout_service.handle_confirm_order(payload)

        async def handle_cancel_intent(message: AbstractIncomingMessage):
            async with message.process():
                payload = json.loads(message.body.decode())
                logger.info(f"Worker processing: intent.cancel for user {payload.get('user_id')}")
                async with SessionLocal() as db:
                    checkout_service = AICheckoutService(db, cache_client, rabbitmq, app_dependencies["payment_orchestrator"])
                    await checkout_service.handle_cancel_order(payload)

        queues_bindings.update({
            "q.ai.chat": ("airdeliver.ai.chat.in", handle_chat_message),
            "q.ai.intent.add": ("airdeliver.ai.intent.add_to_cart", handle_add_intent),
            "q.ai.intent.remove": ("airdeliver.ai.intent.remove_from_cart", handle_remove_intent),
            "q.ai.intent.confirm": ("airdeliver.ai.intent.confirm_order", handle_confirm_intent),
            "q.ai.intent.cancel": ("airdeliver.ai.intent.cancel_order", handle_cancel_intent),
        })

    elif worker_type == "TELEMETRY":
        logger.info(f"--- Initializing {worker_type} Worker ---")
        queues_bindings.update({
            settings.QUEUE_TELEMETRY: (f"drone.telemetry.*", telemetry_consumer.get_telemetry_handler(app_dependencies)),
        })

    elif worker_type == "EVENTS":
        logger.info(f"--- Initializing {worker_type} Worker ---")
        queues_bindings.update({
            settings.QUEUE_EVENTS: (f"drone.events.*", event_consumer.get_event_handler(app_dependencies)),
        })
    else:
        logger.error(f"Unknown WORKER_TYPE: {worker_type}. Exiting.")
        return

    consume_tasks = []
    for q_name, (binding_key, handler) in queues_bindings.items():
        queue = await rabbitmq.channel.declare_queue(q_name, durable=True)
        await queue.bind(rabbitmq.exchange_name, routing_key=binding_key)
        task = asyncio.create_task(queue.consume(handler))
        consume_tasks.append(task)
        logger.info(f"Consumer started for {q_name} on key {binding_key}")

    logger.info(f"--- airdeliver {worker_type} Worker is now running. Press Ctrl+C to stop. ---")

    stop_event = asyncio.Event()

    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutdown signal received...")
    finally:
        logger.info("Shutting down worker...")
        for task in consume_tasks:
            task.cancel()
        await asyncio.gather(*consume_tasks, return_exceptions=True)

        if opensearch_client:
            await opensearch_client.close()
        await rabbitmq.close()
        await cache_client.disconnect()
        logger.info("Worker shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
