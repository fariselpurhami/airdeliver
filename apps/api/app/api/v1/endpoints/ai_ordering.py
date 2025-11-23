# apps/api/app/api/v1/endpoints/ai_ordering.py

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api import deps
from app import models
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import get_cache_client, IAsyncCacheClient
import json
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

logger.info("🚀 AI ORDERING ENDPOINT LOADED: v3.0 (Golden Arch Fix Applied)")

@router.post("/ticket")
async def generate_websocket_ticket(
    current_user: models.User = Depends(deps.get_current_active_user),
    cache: IAsyncCacheClient = Depends(get_cache_client),
):

    ticket = str(uuid.uuid4())
    await cache.set(f"ws_ticket:{ticket}", str(current_user.id), ttl=30)
    return {"ticket": ticket}

@router.websocket("/chat")
async def handle_chat_websocket(
    websocket: WebSocket,
    ticket: str = Query(None),
    session: AsyncSession = Depends(deps.get_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_client),
):
    try:
    
        current_user = await deps.get_current_active_user_ws_ticket(
            websocket=websocket,
            ticket=ticket,
            session=session,
            cache=cache
        )
    except Exception as e:
        logger.error(f"❌ WebSocket Auth Failed: {e}")
    
        if websocket.client_state.value == 1: 
             await websocket.close()
        return 

    await websocket.accept()
    
    connection_manager = deps.get_websocket_manager()
    await connection_manager.connect(current_user.id, websocket)
    
    logger.info(f"✅ User {current_user.id} connected to AI Chat via Secure Ticket.")

    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                continue

            message_payload = {
                "user_id": current_user.id,
                "email": current_user.email,
                "country": current_user.country or "US",
                "phone": current_user.phone_number or "",
                "address": current_user.address or "",
                "city": current_user.city or "",
                "message": message_data.get("message"),
                "type": message_data.get("type", "CHAT_MESSAGE"),
                "timestamp": message_data.get("timestamp"), 
            }
            
            routing_key = "airdeliver.ai.chat.in"
            
            if message_data.get("type") == "CANCEL_INTENT":
                routing_key = "airdeliver.ai.intent.cancel_order"

            await rabbitmq.publish(
                body=message_payload,
                routing_key=routing_key,
            )

    except WebSocketDisconnect:
        logger.info(f"User {current_user.id} disconnected explicitly.")
        await connection_manager.disconnect(current_user.id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {current_user.id}: {e}")
        await connection_manager.disconnect(current_user.id, websocket)
