# apps/api/app/main.py

import logging
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from aio_pika.abc import AbstractIncomingMessage

from app.db.session import engine
from app.api.v1.api import api_router
from app.core.config import get_core_settings, CoreSettings
from app.core.limiter import limiter
from app.websockets.tracking_ws import router as tracking_router
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import RedisCacheClient, NoOpCacheClient, get_cache_client, IAsyncCacheClient
from app.api.deps import get_websocket_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIRECTORY_STR = "/app/static"

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def start_response_consumer(app: FastAPI):
    logger.info("--- Starting AI Response Consumer ---")
    rabbitmq = app.state.rabbitmq
    manager = get_websocket_manager()
    response_queue_name = "q.ai.response.out"
    routing_key = "airdeliver.ai.response.out"

    try:
        queue = await rabbitmq.channel.declare_queue(response_queue_name, durable=True)
        await queue.bind(rabbitmq.exchange_name, routing_key=routing_key)

        async def on_response_message(message: AbstractIncomingMessage):
            async with message.process():
                try:
                    body = message.body.decode()
                    payload = json.loads(body)
                    user_id = payload.get("user_id")

                    if user_id:
                        logger.info(f"Relaying response type '{payload.get('type')}' to user {user_id}")
                        await manager.send_to_user(user_id, body)
                    else:
                        logger.warning("Received AI response with no user_id.")
                except Exception as e:
                    logger.error(f"Failed to process response message: {e}")

        logger.info(f"Consumer listening on {response_queue_name} for {routing_key}")
        await queue.consume(on_response_message)

    except asyncio.CancelledError:
        logger.info("AI Response Consumer stopping.")
    except Exception as e:
        logger.error(f"AI Response Consumer failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Lifespan: Startup ---")

    current_settings = get_core_settings()

    await create_db_and_tables()

    logger.info("--- Lifespan: Warming up Cache connection ---")
    cache_client: IAsyncCacheClient
    if current_settings.USE_REDIS and current_settings.REDIS_URL:
        cache_client = RedisCacheClient(url=current_settings.REDIS_URL)
        await cache_client.connect()
    else:
        cache_client = NoOpCacheClient()
    app.state.cache = cache_client

    logger.info("--- Lifespan: Connecting RabbitMQ ---")
    rabbitmq_instance = await get_rabbitmq_service(current_settings)
    app.state.rabbitmq = rabbitmq_instance

    logger.info("--- Lifespan: Starting AI Response Consumer Task ---")
    consumer_task = asyncio.create_task(start_response_consumer(app))
    app.state.response_consumer_task = consumer_task

    Path(STATIC_DIRECTORY_STR).mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY_STR), name="static")

    logger.info("--- Lifespan: API Ready ---")
    yield

    logger.info("--- Lifespan: Shutdown ---")

    if hasattr(app.state, 'response_consumer_task'):
        logger.info("--- Lifespan: Stopping AI Response Consumer ---")
        app.state.response_consumer_task.cancel()
        try:
            await app.state.response_consumer_task
        except asyncio.CancelledError:
            pass

    if hasattr(app.state, 'rabbitmq') and app.state.rabbitmq:
        await app.state.rabbitmq.close()
    if hasattr(app.state, 'cache') and app.state.cache:
        await app.state.cache.disconnect()
    logger.info("--- Lifespan: Services disconnected ---")

app = FastAPI(
    title="AirDeliver API",
    openapi_url=f"{get_core_settings().API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Handler: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

@app.middleware("http")
async def ensure_utf8_encoding(request: Request, call_next):
    response = await call_next(request)
    if "charset" not in response.headers.get("content-type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

if get_core_settings().BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in get_core_settings().BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=get_core_settings().API_V1_STR)
app.include_router(tracking_router, prefix="/ws")

@app.get("/debug-routes")
async def get_all_routes():
    return JSONResponse(content=[{"path": route.path, "name": route.name} for route in app.routes])

@app.get("/")
def read_root():
    return {"message": "AirDeliver API", "env": get_core_settings().APP_ENV}
