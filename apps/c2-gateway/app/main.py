# apps/c2-gateway/app/main.py

from fastapi import FastAPI
from .core.config import settings
from .api.v1.endpoints import c2_ws
from .services import rabbitmq_service

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
async def startup_event():
    await rabbitmq_service.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await rabbitmq_service.disconnect()

app.include_router(c2_ws.router, prefix=settings.API_V1_STR)
