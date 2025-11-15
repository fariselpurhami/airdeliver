# apps/c2-gateway/app/services/websocket_manager.py

import logging
import json
from fastapi import WebSocket
from app.services.rabbitmq_service import RabbitMQService

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, rabbitmq_service: RabbitMQService):
        self.active_connections: dict[str, WebSocket] = {}
        self.rabbitmq_service = rabbitmq_service

    async def connect(self, websocket: WebSocket, drone_id: str):
        await websocket.accept()
        self.active_connections[drone_id] = websocket
        logger.info(f"Drone {drone_id} connected.")
        await self.rabbitmq_service.subscribe_to_commands(
            drone_id, self.handle_command
        )

    async def disconnect(self, drone_id: str):
        if drone_id in self.active_connections:
            del self.active_connections[drone_id]
            logger.info(f"Drone {drone_id} disconnected.")
        await self.rabbitmq_service.unsubscribe_from_commands(drone_id)

    async def handle_message(self, drone_id: str, message: str):
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "telemetry":
                await self.rabbitmq_service.publish_telemetry(drone_id, data)
            elif message_type == "event":
                await self.rabbitmq_service.publish_event(drone_id, data)
            else:
                logger.warning(f"Unknown message type from {drone_id}: {message_type}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {drone_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {drone_id}: {e}", exc_info=True)

    async def handle_command(self, drone_id: str, command: dict):
        if drone_id in self.active_connections:
            websocket = self.active_connections[drone_id]
            try:
                await websocket.send_json(command)
                logger.info(f"Command sent to {drone_id}: {command.get('command')}")
            except Exception as e:
                logger.error(f"Failed to send command to {drone_id}: {e}", exc_info=True)
        else:
            logger.warning(f"Drone {drone_id} not connected. Cannot send command.")

    async def listen_for_commands(self):
        pass
