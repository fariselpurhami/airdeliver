from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from aio_pika.abc import AbstractIncomingMessage
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
from app.websockets.tracking_ws import router as tracking_router

logger = logging.getLogger(__name__)

STATIC_DIRECTORY = Path("static")
RESPONSE_QUEUE_NAME = "q.ai.response.out"
RESPONSE_ROUTING_KEY = "airdeliver.ai.response.out"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def register_exception_handlers(app: FastAPI) -> None:
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
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
        )

    @app.middleware("http")
    async def ensure_response_charset(request: Request, call_next) -> Response:
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")

        if content_type.startswith("application/json") and "charset=" not in content_type.lower():
            response.headers["Content-Type"] = "application/json; charset=utf-8"

        return response


def decode_message_body(body: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Dropping malformed AI response message.", exc_info=exc)
        raise

    if not isinstance(decoded, dict):
        raise ValueError("Expected RabbitMQ payload to be a JSON object.")

    return decoded


async def start_response_consumer(app: FastAPI) -> None:
    rabbitmq = app.state.rabbitmq
    websocket_manager = get_websocket_manager()

    queue = await rabbitmq.channel.declare_queue(RESPONSE_QUEUE_NAME, durable=True)
    await queue.bind(rabbitmq.exchange_name, routing_key=RESPONSE_ROUTING_KEY)

    async def on_response_message(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            payload = decode_message_body(message.body)

            user_id = payload.get("user_id")
            if not isinstance(user_id, str) or not user_id.strip():
                logger.warning("Dropping AI response without a valid user_id.")
                return

            message_type = payload.get("type", "unknown")
            logger.info(
                "Relaying AI response.",
                extra={
                    "user_id": user_id,
                    "message_type": message_type,
                },
            )
            await websocket_manager.send_to_user(
                user_id,
                json.dumps(payload, separators=(",", ":")),
            )

    logger.info(
        "AI response consumer started.",
        extra={
            "queue": RESPONSE_QUEUE_NAME,
            "routing_key": RESPONSE_ROUTING_KEY,
        },
    )
    await queue.consume(on_response_message)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_core_settings()

    cache_client: IAsyncCacheClient = NoOpCacheClient()
    rabbitmq = None
    consumer_task: asyncio.Task[None] | None = None

    try:
        if settings.USE_REDIS and settings.REDIS_URL:
            cache_client = RedisCacheClient(url=settings.REDIS_URL)
            await cache_client.connect()

        app.state.cache = cache_client

        rabbitmq = await get_rabbitmq_service(settings)
        app.state.rabbitmq = rabbitmq

        STATIC_DIRECTORY.mkdir(parents=True, exist_ok=True)

        consumer_task = asyncio.create_task(
            start_response_consumer(app),
            name="ai-response-consumer",
        )
        app.state.response_consumer_task = consumer_task

        logger.info("Application startup complete.")
        yield

    finally:
        if consumer_task is not None:
            consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer_task

        if rabbitmq is not None:
            await rabbitmq.close()

        await cache_client.disconnect()
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

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")

    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(tracking_router, prefix="/ws")

    @app.get("/", tags=["health"])
    async def read_root() -> dict[str, str]:
        return {
            "service": "airdeliver-api",
            "environment": settings.APP_ENV,
            "status": "ok",
        }

    return app


configure_logging()
app = create_application()
