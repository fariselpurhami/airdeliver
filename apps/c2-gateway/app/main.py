# apps/c2-gateway/app/main.py

import logging
import asyncio

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.services.rabbitmq_service import rabbitmq_service
from app.services.websocket_manager import WebSocketManager
from app.api.v1.handlers import drone_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- C2 Gateway Lifespan: Startup ---")

    logger.info("--- C2 Gateway Lifespan: Connecting RabbitMQ ---")
    await rabbitmq_service.connect()

    app.state.websocket_manager = WebSocketManager(rabbitmq_service)
    asyncio.create_task(app.state.websocket_manager.listen_for_commands())

    logger.info("--- C2 Gateway Lifespan: Ready ---")
    yield

    logger.info("--- C2 Gateway Lifespan: Shutdown ---")
    await rabbitmq_service.disconnect()
    logger.info("--- C2 Gateway Lifespan: Shutdown Complete ---")


app = FastAPI(
    title="airdeliver C2 Gateway",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.websocket("/drones/{drone_id}")
async def websocket_endpoint(websocket: WebSocket, drone_id: str):
    manager = websocket.app.state.websocket_manager

    token = websocket.query_params.get("token")
    if not token or not await drone_auth.validate_drone_token(drone_id, token):
        logger.warning(f"Failed auth attempt for drone {drone_id}")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, drone_id)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(drone_id, data)
    except WebSocketDisconnect:
        logger.info(f"Drone {drone_id} disconnected.")
        await manager.disconnect(drone_id)
    except Exception as e:
        logger.error(f"Error for drone {drone_id}: {e}", exc_info=True)
        await manager.disconnect(drone_id)

@app.get("/ws/health", status_code=200)
async def health_check():
    """
    Health check endpoint for Docker.
    """
    return JSONResponse(content={"status": "ok"})

@app.get("/")
def read_root():
    return {"message": "airdeliver C2 Gateway"}
