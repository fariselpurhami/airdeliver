# apps/api/app/api/v1/endpoints/ai_ordering.py

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from app.api import deps
from app import models
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/chat")
async def handle_chat_websocket(
    websocket: WebSocket,
    token: str = Query(None), 
    settings=Depends(deps.get_core_settings),
    session=Depends(deps.get_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
):
    try:
        current_user = await deps.get_current_active_user_ws(
            websocket, token, settings, session
        )
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        return 

    await websocket.accept()
    
    connection_manager = deps.get_websocket_manager()
    await connection_manager.connect(current_user.id, websocket)
    
    logger.info(f"User {current_user.id} connected to AI Chat.")

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
