import asyncio
import json
import logging
import os
import random
import signal
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Set, TypeAlias

HF_CACHE_ROOT = os.getenv("HF_HOME", "/tmp/huggingface")
HF_HUB_CACHE = os.getenv("HF_HUB_CACHE", f"{HF_CACHE_ROOT}/hub")
HF_DATASETS_CACHE = os.getenv("HF_DATASETS_CACHE", f"{HF_CACHE_ROOT}/datasets")
TRANSFORMERS_CACHE = os.getenv("TRANSFORMERS_CACHE", f"{HF_CACHE_ROOT}/transformers")

os.environ.setdefault("HF_HOME", HF_CACHE_ROOT)
os.environ.setdefault("HF_HUB_CACHE", HF_HUB_CACHE)
os.environ.setdefault("HF_DATASETS_CACHE", HF_DATASETS_CACHE)
os.environ.setdefault("TRANSFORMERS_CACHE", TRANSFORMERS_CACHE)

for cache_dir in (HF_CACHE_ROOT, HF_HUB_CACHE, HF_DATASETS_CACHE, TRANSFORMERS_CACHE):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

import aio_pika
import psutil
import torch
import uvloop
from aiohttp import web
from aio_pika import IncomingMessage, connect_robust
from pymilvus import DataType, MilvusClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from transformers.cache_utils import DynamicCache

from app.core.config import (
    get_core_settings,
    get_mpesa_settings,
    get_paypal_settings,
    get_stripe_settings,
)
from app.services.ai_behavior_engine import BehaviorEngine
from app.services.ai_commerce_engine import (
    AICommerceEngine,
    ai_manager,
    get_ai_commerce_engine,
    get_milvus_client,
    get_opensearch_client,
)
from app.services.ai_nlu_service import AINLUService
from app.services.cache_service import RedisCacheClient
from app.services.free_llm_service import FreeLLMService
from app.services.payment_orchestrator import (
    MpesaGateway,
    PayPalGateway,
    PaymentOrchestrator,
    StripeGateway,
)
from app.services.rabbitmq_service import RabbitMQService

try:
    if not hasattr(DynamicCache, "get_usable_length"):
        def get_usable_length(self, input_seq_len, layer_idx=None):
            return self.get_seq_length(0 if layer_idx is None else layer_idx)
        DynamicCache.get_usable_length = get_usable_length
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | [Worker-Node-Diamond] | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("aio_pika").setLevel(logging.WARNING)
logging.getLogger("aiormq").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("accelerate").setLevel(logging.ERROR)

logger = logging.getLogger("airdeliver.worker")

warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.transformer")
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

WORKER_PREFETCH_DEFAULT = 50
VOICE_LOAD_MAX_RETRIES = 3
VOICE_LOAD_MAX_STABILIZATION_CHECKS = 10
VOICE_LOAD_CPU_THRESHOLD = 50.0
VOICE_LOAD_RAM_THRESHOLD = 85.0
VOICE_LOAD_REQUIRED_VRAM_GB = 6.0
STARTUP_RETRY_MAX_ATTEMPTS = 2
TRANSIENT_RETRY_MAX_ATTEMPTS = 5
MAX_RETRY_BACKOFF_SECONDS = 30.0
HEALTH_SERVER_HOST = "0.0.0.0"
HEALTH_SERVER_PORT = 8081
MAIN_EXCHANGE_NAME = "airdeliver_main_exchange"
BOOTSTRAP_ROUTING_KEY = "airdeliver.ai.chat.in"
BOOTSTRAP_MESSAGE_ID = "worker-bootstrap-initial-suggestions-v1"
READINESS_WAIT_TIMEOUT_SECONDS = 45.0

HandlerFunc: TypeAlias = Callable[[dict], Awaitable[None]]

_shutdown_event = asyncio.Event()
_background_tasks: Set[asyncio.Task[Any]] = set()


class StartupDependencyError(Exception):
    pass


class PermanentProcessingError(Exception):
    pass


class ServiceRegistry:
    def __init__(self) -> None:
        self.rabbitmq: Optional[RabbitMQService] = None
        self.db_engine: Optional[AsyncEngine] = None
        self.cache: Optional[RedisCacheClient] = None
        self.commerce: Optional[Any] = None
        self.session_maker: Optional[sessionmaker] = None
        self.payment: Optional[PaymentOrchestrator] = None
        self.behavior: Optional[BehaviorEngine] = None
        self.llm: Optional[FreeLLMService] = None
        self.consume_connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.consume_channel: Optional[aio_pika.abc.AbstractRobustChannel] = None
        self.health_runner: Optional[web.AppRunner] = None
        self.health_site: Optional[web.BaseSite] = None
        self.opensearch_gen: Optional[Any] = None
        self.opensearch_client: Optional[Any] = None
        self.bootstrap_published: bool = False
        self.infrastructure_ready: bool = False
        self.ai_ready: bool = False
        self.ai_degraded: bool = False
        self.payment_ready: bool = False
        self.consumer_ready: bool = False
        self.readiness_event = asyncio.Event()
        self.startup_error: Optional[str] = None

    def refresh_readiness(self) -> None:
        ready = self.infrastructure_ready and self.consumer_ready and self.payment_ready
        if ready:
            self.readiness_event.set()
        else:
            self.readiness_event.clear()

    async def close(self) -> None:
        for task in list(_background_tasks):
            task.cancel()
        for task in list(_background_tasks):
            with suppress(asyncio.CancelledError, Exception):
                await task

        if self.consume_channel is not None:
            with suppress(Exception):
                await self.consume_channel.close()

        if self.consume_connection is not None:
            with suppress(Exception):
                await self.consume_connection.close()

        if self.rabbitmq is not None:
            close_method = getattr(self.rabbitmq, "close", None)
            if callable(close_method):
                result = close_method()
                if asyncio.iscoroutine(result):
                    with suppress(Exception):
                        await result

        if self.health_runner is not None:
            with suppress(Exception):
                await self.health_runner.cleanup()

        if self.cache is not None:
            close_method = getattr(self.cache, "close", None)
            if callable(close_method):
                result = close_method()
                if asyncio.iscoroutine(result):
                    with suppress(Exception):
                        await result

        if self.db_engine is not None:
            with suppress(Exception):
                await self.db_engine.dispose()

        if self.opensearch_gen is not None:
            with suppress(Exception):
                await self.opensearch_gen.aclose()


services = ServiceRegistry()


class VoiceBrainStatus:
    READY: bool = False
    LOADING: bool = False
    ERROR: Optional[str] = None


def create_background_task(coro: Awaitable[Any], name: str) -> asyncio.Task[Any]:
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)

    def _cleanup(completed: asyncio.Task[Any]) -> None:
        _background_tasks.discard(completed)
        with suppress(asyncio.CancelledError):
            exc = completed.exception()
            if exc is not None:
                logger.error("Background task failed: %s", name, exc_info=exc)

    task.add_done_callback(_cleanup)
    return task


def install_signal_handlers() -> None:
    loop = asyncio.get_running_loop()

    def _trigger_shutdown(received_signal: signal.Signals) -> None:
        logger.warning("Signal received: %s", received_signal.name)
        _shutdown_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, partial(_trigger_shutdown, signum))


def ensure_milvus_schema(client: MilvusClient) -> None:
    schema_config = AICommerceEngine.SCHEMA_CONFIG
    text_config = schema_config["product_text"]
    visual_config = schema_config["product_visual"]

    text_collection_name = str(text_config["name"])
    visual_collection_name = str(visual_config["name"])
    text_dimension = int(text_config["dim"])
    visual_dimension = int(visual_config["dim"])

    try:
        if not client.has_collection(collection_name=text_collection_name):
            text_schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            text_schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            text_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=text_dimension)
            text_schema.add_field(field_name="price", datatype=DataType.FLOAT)
            text_schema.add_field(field_name="category", datatype=DataType.VARCHAR, max_length=128)

            text_index_params = client.prepare_index_params()
            text_index_params.add_index(
                field_name="vector",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 16, "efConstruction": 200},
            )

            client.create_collection(
                collection_name=text_collection_name,
                schema=text_schema,
                index_params=text_index_params,
            )

        if not client.has_collection(collection_name=visual_collection_name):
            visual_schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            visual_schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            visual_schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=visual_dimension)

            visual_index_params = client.prepare_index_params()
            visual_index_params.add_index(
                field_name="vector",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 16, "efConstruction": 200},
            )

            client.create_collection(
                collection_name=visual_collection_name,
                schema=visual_schema,
                index_params=visual_index_params,
            )
    except Exception:
        logger.exception("Milvus schema initialization failed")
        raise

def is_message_startup_dependent(payload: dict) -> bool:
    message_type = str(payload.get("type", "")).upper()
    message_text = str(payload.get("message", ""))
    return message_type == "WELCOME_INTENT" or message_text == "__INTERNAL_GET_INITIAL_SUGGESTIONS__"


async def wait_for_readiness(required_ai: bool = False, timeout: float = READINESS_WAIT_TIMEOUT_SECONDS) -> None:
    try:
        await asyncio.wait_for(services.readiness_event.wait(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise StartupDependencyError("WORKER_NOT_READY") from exc

    if services.session_maker is None or services.cache is None or services.rabbitmq is None:
        raise StartupDependencyError("CORE_SERVICES_NOT_READY")

    if required_ai and services.commerce is None:
        raise StartupDependencyError("AI_SERVICES_NOT_READY")


async def _track_behavior(user_id: Any, action: str, metadata: Dict[str, Any]) -> None:
    if not user_id or services.behavior is None:
        return
    await services.behavior.track_interaction(user_id, action, metadata)


async def lazy_load_voice_brain() -> None:
    VoiceBrainStatus.LOADING = True
    VoiceBrainStatus.READY = False
    VoiceBrainStatus.ERROR = None

    for _ in range(VOICE_LOAD_MAX_STABILIZATION_CHECKS):
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram_usage = psutil.virtual_memory().percent
        if cpu_usage < VOICE_LOAD_CPU_THRESHOLD and ram_usage < VOICE_LOAD_RAM_THRESHOLD:
            break
        await asyncio.sleep(2)

    if torch.cuda.is_available():
        free_mem, _ = torch.cuda.mem_get_info()
        free_mem_gb = free_mem / (1024 ** 3)
        if free_mem_gb < VOICE_LOAD_REQUIRED_VRAM_GB:
            VoiceBrainStatus.LOADING = False
            VoiceBrainStatus.READY = False
            VoiceBrainStatus.ERROR = "OOM_RISK"
            logger.critical(
                "Insufficient GPU memory for voice brain initialization: free=%.2fGB required=%.2fGB",
                free_mem_gb,
                VOICE_LOAD_REQUIRED_VRAM_GB,
            )
            return

    loop = asyncio.get_running_loop()

    for attempt in range(1, VOICE_LOAD_MAX_RETRIES + 1):
        try:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="VoiceBrainLoader") as executor:
                load_fn = getattr(ai_manager, "load_personaplex_model", None)
                if callable(load_fn):
                    await loop.run_in_executor(executor, load_fn)

            if services.rabbitmq is not None and not services.bootstrap_published:
                await services.rabbitmq.publish(
                    {
                        "user_id": 1,
                        "message": "__INTERNAL_GET_INITIAL_SUGGESTIONS__",
                        "type": "WELCOME_INTENT",
                        "message_id": BOOTSTRAP_MESSAGE_ID,
                    },
                    BOOTSTRAP_ROUTING_KEY,
                )
                services.bootstrap_published = True

            VoiceBrainStatus.LOADING = False
            VoiceBrainStatus.READY = True
            VoiceBrainStatus.ERROR = None
            logger.info("Voice brain initialized successfully")
            return
        except Exception as exc:
            VoiceBrainStatus.READY = False
            VoiceBrainStatus.ERROR = str(exc)
            logger.warning("Voice brain initialization attempt %s failed", attempt, exc_info=exc)
            if attempt >= VOICE_LOAD_MAX_RETRIES:
                break
            await asyncio.sleep(2 ** attempt)

    VoiceBrainStatus.LOADING = False
    VoiceBrainStatus.READY = False
    if VoiceBrainStatus.ERROR is None:
        VoiceBrainStatus.ERROR = "MAX_RETRIES_EXCEEDED"
    logger.critical("Voice brain failed to initialize; worker continues in degraded mode")


async def save_cart_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=False)

    async with services.session_maker() as db:
        user_id = payload.get("user_id")
        if user_id and services.behavior is not None:
            create_background_task(
                _track_behavior(user_id, "save", {"context": "cart_recovery"}),
                "behavior-save-cart",
            )

        from app.services.ai_cart_service import AICartService

        service = AICartService(db, services.cache, services.rabbitmq, services.commerce)
        await service.handle_save_cart(payload)


async def cancel_order_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=False)

    async with services.session_maker() as db:
        user_id = payload.get("user_id")
        if user_id and services.behavior is not None:
            create_background_task(
                _track_behavior(user_id, "cancel", {"context": "recovery_discard"}),
                "behavior-cancel-order",
            )

        from app.services.ai_checkout_service import AICheckoutService

        service = AICheckoutService(db, services.cache, services.rabbitmq, services.payment)
        await service.handle_cancel_order(payload)


async def smart_retry_wrapper(message: IncomingMessage, handler_func: HandlerFunc) -> None:
    async with message.process(ignore_processed=True):
        try:
            payload = json.loads(message.body.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Malformed JSON payload rejected")
            await message.reject(requeue=False)
            return

        headers = dict(message.headers or {})
        startup_retry_count = int(headers.get("x-startup-retry-count", 0))
        transient_retry_count = int(headers.get("x-transient-retry-count", 0))

        try:
            await handler_func(payload)
            await message.ack()
        except PermanentProcessingError as exc:
            logger.error("Permanent processing error; message rejected: %s", exc)
            await message.reject(requeue=False)
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("Terminal logic error; message rejected: %s", exc)
            await message.reject(requeue=False)
        except StartupDependencyError as exc:
            if is_message_startup_dependent(payload) and startup_retry_count < STARTUP_RETRY_MAX_ATTEMPTS:
                backoff_time = min(2 ** startup_retry_count, 10.0)
                logger.warning(
                    "Startup dependency unavailable: %s. local-retry=%s/%s backoff=%.2fs",
                    exc,
                    startup_retry_count + 1,
                    STARTUP_RETRY_MAX_ATTEMPTS,
                    backoff_time,
                )
                await asyncio.sleep(backoff_time)
                headers["x-startup-retry-count"] = startup_retry_count + 1
                await handler_func(payload)
                await message.ack()
                return

            logger.error("Startup dependency unavailable; message rejected without requeue: %s", exc)
            await message.reject(requeue=False)
        except Exception as exc:
            if transient_retry_count < TRANSIENT_RETRY_MAX_ATTEMPTS:
                backoff_time = min((2 ** transient_retry_count) + random.uniform(0.1, 1.0), MAX_RETRY_BACKOFF_SECONDS)
                logger.warning(
                    "Transient processing failure: %s. local-retry=%s/%s backoff=%.2fs",
                    type(exc).__name__,
                    transient_retry_count + 1,
                    TRANSIENT_RETRY_MAX_ATTEMPTS,
                    backoff_time,
                )
                await asyncio.sleep(backoff_time)
                headers["x-transient-retry-count"] = transient_retry_count + 1
                await handler_func(payload)
                await message.ack()
                return

            logger.critical("Message dropped after max retries: %s", exc, exc_info=exc)
            await message.reject(requeue=False)


async def health_check_handler(request: web.Request) -> web.Response:
    rabbitmq_ready = services.rabbitmq is not None and not getattr(services.rabbitmq, "is_closed", False)
    db_ready = services.db_engine is not None
    ai_ready = services.ai_ready
    ready = services.readiness_event.is_set()

    status_details = {
        "version": "Diamond-V31",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rabbitmq": "connected" if rabbitmq_ready else "disconnected",
        "db": "ready" if db_ready else "not_initialized",
        "ai_engine": "online" if ai_ready else ("degraded" if services.ai_degraded else "warming_up"),
        "payment": "ready" if services.payment_ready else "not_ready",
        "consumers": "ready" if services.consumer_ready else "not_ready",
        "readiness": ready,
        "startup_error": services.startup_error,
        "voice_brain": {
            "ready": VoiceBrainStatus.READY,
            "loading": VoiceBrainStatus.LOADING,
            "error": VoiceBrainStatus.ERROR,
        },
    }

    healthy = rabbitmq_ready and db_ready
    status_code = 200 if healthy else 503
    return web.json_response(
        {"status": "healthy" if healthy else "unhealthy", "details": status_details},
        status=status_code,
    )


async def readiness_check_handler(request: web.Request) -> web.Response:
    ready = services.readiness_event.is_set()
    status_code = 200 if ready else 503
    return web.json_response(
        {
            "status": "ready" if ready else "not_ready",
            "details": {
                "infrastructure_ready": services.infrastructure_ready,
                "consumer_ready": services.consumer_ready,
                "payment_ready": services.payment_ready,
                "ai_ready": services.ai_ready,
                "ai_degraded": services.ai_degraded,
                "startup_error": services.startup_error,
            },
        },
        status=status_code,
    )


async def start_health_server() -> None:
    app = web.Application()
    app.add_routes(
        [
            web.get("/health", health_check_handler),
            web.get("/ready", readiness_check_handler),
        ]
    )
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HEALTH_SERVER_HOST, HEALTH_SERVER_PORT)
    await site.start()
    services.health_runner = runner
    services.health_site = site
    logger.info("Health check server listening on %s:%s", HEALTH_SERVER_HOST, HEALTH_SERVER_PORT)


async def chat_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=True)

    async with services.session_maker() as db:
        service = AINLUService(
            db=db,
            search_engine=services.commerce,
            rabbitmq=services.rabbitmq,
            cache=services.cache,
            llm_service=services.llm or FreeLLMService(),
            behavior_engine=services.behavior,
        )

        user_id = payload.get("user_id")
        if user_id and services.behavior is not None:
            create_background_task(
                _track_behavior(user_id, "search", {"query": payload.get("message", "")}),
                "behavior-chat-search",
            )

        await service.process_message(payload)


async def add_cart_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=False)

    async with services.session_maker() as db:
        user_id = payload.get("user_id")
        if user_id and services.behavior is not None:
            create_background_task(
                _track_behavior(
                    user_id,
                    "cart",
                    {"id": payload.get("product_id"), "action": "add"},
                ),
                "behavior-add-cart",
            )

        from app.services.ai_cart_service import AICartService

        cart_service = AICartService(
            db,
            services.cache,
            services.rabbitmq,
            commerce_engine=services.commerce,
        )
        await cart_service.handle_add_to_cart(payload)


async def remove_cart_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=False)

    async with services.session_maker() as db:
        user_id = payload.get("user_id")
        if user_id and services.behavior is not None:
            create_background_task(
                _track_behavior(user_id, "discard", {"id": payload.get("product_id")}),
                "behavior-remove-cart",
            )

        from app.services.ai_cart_service import AICartService

        cart_service = AICartService(
            db,
            services.cache,
            services.rabbitmq,
            commerce_engine=services.commerce,
        )
        await cart_service.handle_remove_from_cart(payload)


async def clear_cart_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=False)

    async with services.session_maker() as db:
        from app.services.ai_cart_service import AICartService

        service = AICartService(db, services.cache, services.rabbitmq)
        await service.handle_clear_cart(payload)


async def confirm_order_handler_impl(payload: dict) -> None:
    await wait_for_readiness(required_ai=False)

    async with services.session_maker() as db:
        user_id = payload.get("user_id")
        if user_id and services.behavior is not None:
            create_background_task(
                _track_behavior(user_id, "buy", {"context": "checkout_initiated"}),
                "behavior-confirm-order",
            )

        from app.services.ai_checkout_service import AICheckoutService

        checkout_service = AICheckoutService(
            db,
            services.cache,
            services.rabbitmq,
            services.payment,
        )
        await checkout_service.handle_confirm_order(payload)


async def initialize_infrastructure() -> RedisCacheClient:
    settings = get_core_settings()

    db_engine = create_async_engine(
        str(settings.DATABASE_URI),
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=50,
        max_overflow=20,
    )
    session_maker_factory = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    cache_client = RedisCacheClient(str(settings.REDIS_URL))
    connect_method = getattr(cache_client, "connect", None)
    if callable(connect_method):
        result = connect_method()
        if asyncio.iscoroutine(result):
            await result

    services.db_engine = db_engine
    services.session_maker = session_maker_factory
    services.cache = cache_client
    services.infrastructure_ready = True
    services.refresh_readiness()
    return cache_client


async def initialize_ai(cache_client: RedisCacheClient) -> None:
    settings = get_core_settings()
    services.opensearch_gen = get_opensearch_client(settings)
    services.opensearch_client = await anext(services.opensearch_gen)

    milvus_client = get_milvus_client(settings)
    ensure_milvus_schema(milvus_client)

    loop = asyncio.get_running_loop()
    embedding_model = await loop.run_in_executor(None, ai_manager.get_text_model)

    vision_loader = getattr(ai_manager, "get_vision_stack", None)
    if callable(vision_loader):
        await loop.run_in_executor(None, vision_loader)
    else:
        fallback_vision_loader = getattr(ai_manager, "get_vision_model", None) or getattr(ai_manager, "get_image_model", None)
        if callable(fallback_vision_loader):
            await loop.run_in_executor(None, fallback_vision_loader)

    services.commerce = get_ai_commerce_engine(
        services.opensearch_client,
        milvus_client,
        embedding_model,
        cache_client,
    )
    services.llm = FreeLLMService()
    services.behavior = BehaviorEngine(cache_client)
    services.ai_ready = True
    services.ai_degraded = False


def initialize_payment(cache_client: RedisCacheClient) -> None:
    services.payment = PaymentOrchestrator(
        StripeGateway(get_stripe_settings()),
        PayPalGateway(get_paypal_settings(), cache_client),
        MpesaGateway(get_mpesa_settings(), cache_client),
    )
    services.payment_ready = True
    services.refresh_readiness()


async def initialize_rabbitmq_consumers() -> None:
    settings = get_core_settings()
    rabbitmq_service = RabbitMQService(settings)
    services.rabbitmq = rabbitmq_service

    consume_connection = await connect_robust(str(settings.RABBITMQ_URL))
    consume_channel = await consume_connection.channel()
    await consume_channel.set_qos(
        prefetch_count=int(os.getenv("WORKER_PREFETCH", str(WORKER_PREFETCH_DEFAULT)))
    )

    exchange = await consume_channel.declare_exchange(
        MAIN_EXCHANGE_NAME,
        type="topic",
        durable=True,
    )

    queue_config: Dict[str, Dict[str, Any]] = {
        "chat": {
            "queue": "q.ai.chat",
            "key": "airdeliver.ai.chat.in",
            "handler": chat_handler_impl,
        },
        "cart_add": {
            "queue": "q.ai.cart.add",
            "key": "airdeliver.ai.cart.add",
            "handler": add_cart_handler_impl,
        },
        "cart_remove": {
            "queue": "q.ai.cart.remove",
            "key": "airdeliver.ai.cart.remove",
            "handler": remove_cart_handler_impl,
        },
        "cart_clear": {
            "queue": "q.ai.cart.clear",
            "key": "airdeliver.ai.cart.clear",
            "handler": clear_cart_handler_impl,
        },
        "checkout": {
            "queue": "q.ai.order.confirm",
            "key": "airdeliver.ai.order.confirm",
            "handler": confirm_order_handler_impl,
        },
        "cancel": {
            "queue": "q.ai.intent.cancel",
            "key": "airdeliver.ai.intent.cancel_order",
            "handler": cancel_order_handler_impl,
        },
        "save": {
            "queue": "q.ai.cart.save",
            "key": "airdeliver.ai.cart.save",
            "handler": save_cart_handler_impl,
        },
    }

    queue_arguments = {"x-queue-type": "quorum"}

    for config in queue_config.values():
        queue = await consume_channel.declare_queue(
            config["queue"],
            durable=True,
            arguments=queue_arguments,
        )
        await queue.bind(exchange, routing_key=config["key"])
        await queue.consume(partial(smart_retry_wrapper, handler_func=config["handler"]))
        logger.info("Bound queue %s", config["queue"])

    services.consume_connection = consume_connection
    services.consume_channel = consume_channel
    services.consumer_ready = True
    services.refresh_readiness()


async def main() -> None:
    install_signal_handlers()
    logger.info("Starting worker node")

    await start_health_server()

    try:
        cache_client = await initialize_infrastructure()
        logger.info("Infrastructure initialized")
    except Exception as exc:
        services.startup_error = "INFRASTRUCTURE_INIT_FAILED"
        logger.critical("Infrastructure initialization failed", exc_info=exc)
        raise

    try:
        await initialize_ai(cache_client)
        logger.info("AI services initialized")
    except Exception as exc:
        services.ai_ready = False
        services.ai_degraded = True
        services.startup_error = "AI_INIT_DEGRADED"
        logger.error("AI initialization failed; worker continues in degraded mode", exc_info=exc)

    try:
        initialize_payment(cache_client)
        logger.info("Payment orchestration initialized")
    except Exception as exc:
        services.startup_error = "PAYMENT_INIT_FAILED"
        logger.critical("Payment initialization failed", exc_info=exc)
        raise

    try:
        await initialize_rabbitmq_consumers()
        logger.info("RabbitMQ consumers initialized")
    except Exception as exc:
        services.startup_error = "RABBITMQ_CONSUMER_INIT_FAILED"
        logger.critical("RabbitMQ consumer initialization failed", exc_info=exc)
        raise

    create_background_task(lazy_load_voice_brain(), "lazy-load-voice-brain")

    logger.info(
        "Worker node operational; ai_ready=%s ai_degraded=%s readiness=%s",
        services.ai_ready,
        services.ai_degraded,
        services.readiness_event.is_set(),
    )

    await _shutdown_event.wait()
    logger.info("Shutdown requested")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt")
    except Exception as exc:
        logger.critical("Worker terminated due to fatal error", exc_info=exc)
        sys.exit(1)
    finally:
        try:
            asyncio.run(services.close())
        except RuntimeError:
            pass
