# apps/api/app/main.py  

import logging
import asyncio
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

from app.db.session import engine
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.websockets.tracking_ws import router as tracking_router
from app.services.rabbitmq_service import rabbitmq_service
from app.services import telemetry_consumer, event_consumer
from app.services.cache_service import RedisCacheClient, NoOpCacheClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIRECTORY_STR = "/app/static"

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Lifespan: Startup ---")
    await create_db_and_tables()

    cache_client = NoOpCacheClient()
    if settings.USE_REDIS and settings.REDIS_URL:
        logger.info("--- Lifespan: Warming up Redis connection ---")
        cache_client = RedisCacheClient(url=settings.REDIS_URL)
        await cache_client.connect()
    
    app.state.cache = cache_client

    logger.info("--- Lifespan: Connecting RabbitMQ ---")
    await rabbitmq_service.connect()
    
    consumer_tasks = []
    if rabbitmq_service.connection_pool:
        task1 = asyncio.create_task(telemetry_consumer.consume_telemetry(rabbitmq_service.connection_pool))
        task2 = asyncio.create_task(event_consumer.consume_events(rabbitmq_service.connection_pool))
        consumer_tasks.extend([task1, task2])
        logger.info("--- Lifespan: Consumers Started ---")
    
    Path(STATIC_DIRECTORY_STR).mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY_STR), name="static")

    logger.info("--- Lifespan: Ready ---")
    yield
    
    logger.info("--- Lifespan: Shutdown ---")
    for task in consumer_tasks:
        task.cancel()
    await asyncio.gather(*consumer_tasks, return_exceptions=True)
    
    await rabbitmq_service.disconnect()
    await app.state.cache.disconnect()

app = FastAPI(
    title="AirDeliver API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
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

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(tracking_router, prefix="/ws")

@app.get("/debug-routes")
async def get_all_routes():
    return JSONResponse(content=[{"path": route.path, "name": route.name} for route in app.routes])

@app.get("/")
def read_root():
    return {"message": "AirDeliver API", "env": settings.APP_ENV}
