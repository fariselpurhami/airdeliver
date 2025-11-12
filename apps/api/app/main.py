# apps/api/app/main.py

import logging
from contextlib import asynccontextmanager
import importlib
import os
import asyncio
from app.db import base
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from app.db.session import engine
from starlette.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.v1.api import api_router
from app.core.config import settings
from app.websockets.tracking_ws import router as tracking_router
from app.services.rabbitmq_service import rabbitmq_service
from app.services import telemetry_consumer, event_consumer
from app.core.limiter import limiter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from pathlib import Path

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Lifespan: Running startup tasks ---")

    await create_db_and_tables()
    
    print("--- Lifespan: Connecting to RabbitMQ ---")
    await rabbitmq_service.connect()
    
    consumer_tasks = []
    if rabbitmq_service.connection_pool:
        task1 = asyncio.create_task(telemetry_consumer.consume_telemetry(rabbitmq_service.connection_pool))
        task2 = asyncio.create_task(event_consumer.consume_events(rabbitmq_service.connection_pool))
        consumer_tasks.extend([task1, task2])
        print("--- Lifespan: RabbitMQ Telemetry and Event consumers started ---")
    else:
        logging.error("--- Lifespan: FAILED to start RabbitMQ consumers. Pool not available. ---")

    print("--- Lifespan: Ensuring static directory exists ---")
    Path(STATIC_DIRECTORY_STR).mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY_STR), name="static")

    print("--- Lifespan: Startup complete. Yielding control. ---")
    yield
    
    print("--- Lifespan: Running shutdown tasks ---")
    for task in consumer_tasks:
        task.cancel()
    await asyncio.gather(*consumer_tasks, return_exceptions=True)
    await rabbitmq_service.disconnect()
    print("--- Lifespan: RabbitMQ connection closed. ---")

app = FastAPI(
    title="airdeliver API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/debug-routes")
async def get_all_routes():
    route_list = []
    for route in app.routes:
        if hasattr(route, "methods"):
            route_list.append({
                "path": route.path,
                "name": route.name,
                "methods": list(route.methods) if route.methods else []
            })
        elif isinstance(route, importlib.import_module('starlette.routing').WebSocketRoute):
             route_list.append({
                 "path": route.path,
                 "name": route.name,
                 "methods": ["WEBSOCKET"]
             })
        elif isinstance(route, importlib.import_module('starlette.routing').Mount):
             route_list.append({
                 "path": route.path + "/*", 
                 "name": route.name,
                 "methods": ["MOUNTED"]
             })
    return JSONResponse(content=route_list)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": f"An unexpected server error occurred. Please check the logs."},
    )

@app.middleware("http")
async def ensure_utf8_encoding(request: Request, call_next):
    response = await call_next(request)
    if "charset" not in response.headers.get("content-type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-f"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIRECTORY_STR = "/app/static"

app.include_router(api_router, prefix=settings.API_V1_STR)

app.include_router(tracking_router, prefix="/ws")

@app.get("/ws/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Welcome to airdeliver API"}
