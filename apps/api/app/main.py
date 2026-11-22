from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Protocol, cast

from aio_pika.abc import AbstractIncomingMessage
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.api.deps import get_websocket_manager
from app.api.v1.api import api_router
from app.core.config import CoreSettings, get_core_settings
from app.core.limiter import limiter
from app.services.cache_service import IAsyncCacheClient, NoOpCacheClient, RedisCacheClient
from app.services.rabbitmq_service import get_rabbitmq_service
from app.services.ai_cart_service import CartPersistenceError
from app.services.ai_behavior_engine import BehaviorEngine
from app.services.ai_commerce_engine import initialize_query_embeddings

from app.websockets.voice_ws import router as voice_router

logger = logging.getLogger(__name__)

STATIC_DIRECTORY = Path("static")
RESPONSE_QUEUE_NAME = "q.ai.response.out"
RESPONSE_ROUTING_KEY = "airdeliver.ai.response.out"
METRICS_ENDPOINT = "/metrics"
HEALTH_ENDPOINT = "/"

def register_routes(app: FastAPI, settings: CoreSettings) -> None:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")

    # Register REST API
    app.include_router(api_router, prefix=settings.API_V1_STR)


    # --- NEW ROUTER REGISTRATION ---
    # Mounts at: /api/v1/ordering/voice-stream
    app.include_router(voice_router, prefix=f"{settings.API_V1_STR}/ordering")

    @app.get(HEALTH_ENDPOINT, tags=["health"])
    async def read_root() -> dict[str, str]:
        return build_health_payload(settings)

class WebSocketManagerProtocol(Protocol):
    async def send_to_user(self, user_id: int, message: str) -> None:
        ...


@dataclass(slots=True)
class ApplicationResources:
    cache: IAsyncCacheClient
    rabbitmq: Any
    response_consumer_task: asyncio.Task[None] | None = None
    behavior: BehaviorEngine | None = None


class InvalidMessageError(ValueError):
    """Raised when an inbound broker payload is invalid for the application contract."""


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_app_resources(app: FastAPI) -> ApplicationResources:
    resources = getattr(app.state, "resources", None)
    if not isinstance(resources, ApplicationResources):
        raise RuntimeError("Application resources are not initialized.")
    return resources


def ensure_static_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def decode_message_body(body: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidMessageError("Broker payload is not valid UTF-8 JSON.") from exc

    if not isinstance(decoded, dict):
        raise InvalidMessageError("Broker payload must be a JSON object.")

    return decoded


def extract_user_id(payload: dict[str, Any]) -> int:
    raw_user_id = payload.get("user_id")
    if isinstance(raw_user_id, bool):
        raise InvalidMessageError("Broker user_id must identify a positive integer user.")
    if isinstance(raw_user_id, int) and raw_user_id > 0:
        return raw_user_id
    if isinstance(raw_user_id, str):
        value = raw_user_id.strip()
        if value.isascii() and value.isdigit() and len(value) <= 20 and int(value) > 0:
            return int(value)
    raise InvalidMessageError("Broker user_id must identify a positive integer user.")


def compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def build_health_payload(settings: CoreSettings) -> dict[str, str]:
    return {
        "service": "airdeliver-api",
        "environment": settings.APP_ENV,
        "status": "ok",
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CartPersistenceError)
    async def cart_persistence_error(request: Request, exc: CartPersistenceError) -> JSONResponse:
        return JSONResponse(status_code=503, headers={"Retry-After": "2", "Cache-Control": "no-store"},
            content={"detail": "Cart state could not be confirmed. Refresh your cart before retrying."})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled application exception.",
            extra={
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=500,
            content={"message": "Internal Server Error"},
        )


def register_middleware(app: FastAPI, settings: CoreSettings) -> None:
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "Idempotency-Key", "X-Requested-With"],
        )

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), payment=(self)")
        # Strict CSP for API responses (JSON). Swagger/ReDoc HTML pages load
        # their JS/CSS from a CDN, so they keep a documentation-only policy.
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'",
            )
        else:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        if settings.APP_ENV == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response

    @app.middleware("http")
    async def ensure_response_charset(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")

        if content_type.startswith("application/json") and "charset=" not in content_type.lower():
            response.headers["Content-Type"] = "application/json; charset=utf-8"

        return response


async def relay_response_message(
    message: AbstractIncomingMessage,
    websocket_manager: WebSocketManagerProtocol,
    cache: IAsyncCacheClient | None = None,
) -> None:
    async with message.process(requeue=True):
        try:
            payload = decode_message_body(message.body)
            user_id = extract_user_id(payload)
        except InvalidMessageError as exc:
            logger.warning(
                "Dropping invalid AI response message.",
                extra={"reason": str(exc)},
            )
            return

        message_type = payload.get("type", "unknown")
        if not isinstance(message_type, str):
            message_type = "unknown"

        serialized = compact_json(payload)
        if cache is not None and not isinstance(cache, NoOpCacheClient):
            # The socket already subscribes to this user-specific Redis
            # channel. Publishing here reaches it regardless of which API
            # process consumed the shared durable RabbitMQ queue.
            for attempt in range(3):
                try:
                    await asyncio.wait_for(cache.publish_required(f"airdeliver:response:{user_id}", serialized), timeout=5.0)
                    break
                except (RedisConnectionError, RedisTimeoutError, OSError, asyncio.TimeoutError):
                    if attempt == 2:
                        logger.exception("Response Redis bridge unavailable; broker delivery will requeue")
                        raise
                    await asyncio.sleep(2 ** attempt)
        else:
            # Development without Redis supports a single local process.
            await websocket_manager.send_to_user(user_id, serialized)

        logger.info(
            "Relayed AI response.",
            extra={
                "user_id": user_id,
                "message_type": message_type,
            },
        )


async def start_response_consumer(app: FastAPI) -> None:
    resources = get_app_resources(app)
    rabbitmq = resources.rabbitmq
    websocket_manager = cast(WebSocketManagerProtocol, get_websocket_manager())

    await rabbitmq.consume(
        RESPONSE_QUEUE_NAME,
        RESPONSE_ROUTING_KEY,
        lambda message: relay_response_message(message=message, websocket_manager=websocket_manager, cache=resources.cache),
    )
    logger.info("AI response consumer bound", extra={"queue": RESPONSE_QUEUE_NAME, "routing_key": RESPONSE_ROUTING_KEY})


async def initialize_cache_client(settings: CoreSettings) -> IAsyncCacheClient:
    if settings.USE_REDIS and settings.REDIS_URL:
        cache_client: IAsyncCacheClient = RedisCacheClient(url=settings.REDIS_URL)
        await cache_client.connect()
        logger.info("Redis cache client connected.")
        return cache_client

    logger.info("Redis disabled or not configured. Falling back to NoOp cache client.")
    return NoOpCacheClient()


def configure_metrics(app: FastAPI) -> None:
    Instrumentator().instrument(app).expose(
        app,
        endpoint=METRICS_ENDPOINT,
        include_in_schema=False,
    )


def register_routes(app: FastAPI, settings: CoreSettings) -> None:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")

    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get(HEALTH_ENDPOINT, tags=["health"])
    async def read_root() -> dict[str, str]:
        return build_health_payload(settings)


async def startup_resources(app: FastAPI, settings: CoreSettings) -> ApplicationResources:
    cache_client = await initialize_cache_client(settings)
    rabbitmq = await get_rabbitmq_service(settings)

    resources = ApplicationResources(
        cache=cache_client,
        rabbitmq=rabbitmq,
    )

    app.state.cache = cache_client
    app.state.rabbitmq = rabbitmq
    app.state.resources = resources

    try:
        resources.behavior = BehaviorEngine(cache_client)
        app.state.behavior = resources.behavior
        await resources.behavior.start()
        # Queue binding is startup work, not a detached task that can fail
        # unnoticed while the API reports a successful startup.
        await start_response_consumer(app)
    except BaseException:
        await shutdown_resources(resources)
        raise
    app.state.response_consumer_task = None

    return resources


async def shutdown_resources(resources: ApplicationResources) -> None:
    if resources.behavior is not None:
        await resources.behavior.stop()
    if resources.response_consumer_task is not None:
        resources.response_consumer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await resources.response_consumer_task

    with contextlib.suppress(Exception):
        await resources.rabbitmq.close()

    with contextlib.suppress(Exception):
        await resources.cache.disconnect()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_core_settings()
    ensure_static_directory(STATIC_DIRECTORY)

    resources: ApplicationResources | None = None
    try:
        resources = await startup_resources(app, settings)
        await initialize_query_embeddings()
        logger.info("Application startup complete.")
        yield
    finally:
        if resources is not None:
            await shutdown_resources(resources)
        logger.info("Application shutdown complete.")


def create_application() -> FastAPI:
    settings = get_core_settings()

    app = FastAPI(
        title="airdeliver API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    register_middleware(app, settings)
    register_exception_handlers(app)
    configure_metrics(app)
    register_routes(app, settings)

    return app


configure_logging()
app = create_application()
