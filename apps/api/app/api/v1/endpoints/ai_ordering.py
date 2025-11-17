# apps/api/app/api/v1/endpoints/ai_ordering.py

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from app.api import deps
from app import models
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
import json

router = APIRouter()

@router.websocket("/chat")
async def handle_chat_websocket(
    websocket: WebSocket,
    current_user: models.User = Depends(deps.get_current_active_user_ws),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
):
    await websocket.accept()

    connection_manager = deps.get_websocket_manager()
    await connection_manager.connect(current_user.id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message_payload = {
                "user_id": current_user.id,
                "email": current_user.email,
                "country": current_user.country or "US",
                "phone": current_user.phone_number or "",
                "address": current_user.address or "",
                "city": current_user.city or "",
                "message": message_data.get("message"),
                "type": message_data.get("type", "CHAT_MESSAGE"),
            }

            await rabbitmq.publish(
                body=message_payload,
                routing_key="airdeliver.ai.chat.in",
            )

    except WebSocketDisconnect:
        await connection_manager.disconnect(current_user.id)
    except Exception as e:
        await connection_manager.disconnect(current_user.id)
