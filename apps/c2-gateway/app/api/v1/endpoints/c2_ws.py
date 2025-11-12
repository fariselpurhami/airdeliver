# apps/c2-gateway/app/api/v1/endpoints/c2_ws.py

from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool
import aio_pika
import asyncio
import logging
import json
from app.core.config import settings
from app.core.auth import get_drone_id_from_token
from app.services.rabbitmq_service import rabbitmq_service

router = APIRouter()

async def get_connection() -> AbstractRobustConnection:
    return await aio_pika.connect_robust(settings.RABBITMQ_URL)

@router.websocket("/ws/connect/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    drone_id = None
    try:
        drone_id = await get_drone_id_from_token(f"Bearer {token}")
    except Exception as e:
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid auth token")
        return

    await websocket.accept()
    logging.info(f"Drone {drone_id} connected via WebSocket.")

    connection_pool = Pool(get_connection, max_size=2)
    command_queue = None

    async def consume_commands(queue: aio_pika.abc.AbstractQueue):
        try:
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            await websocket.send_text(message.body.decode())
                        except WebSocketDisconnect:
                            logging.warning(f"WS disconnected for {drone_id} during command send.")
                            break
                        except Exception as e:
                            logging.error(f"Error sending command to {drone_id}: {e}")
        except asyncio.CancelledError:
            logging.info(f"Command consumer for {drone_id} cancelled.")
        except Exception as e:
            logging.error(f"Command consumer for {drone_id} crashed: {e}")

    async def receive_messages():
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                msg_type = message.get("type")
                
                routing_key = f"drone.{drone_id}"
                
                if msg_type == "telemetry":
                    await rabbitmq_service.publish_message(
                        settings.EXCHANGE_TELEMETRY, routing_key, data.encode()
                    )
                elif msg_type == "event":
                    await rabbitmq_service.publish_message(
                        settings.EXCHANGE_EVENTS, routing_key, data.encode()
                    )
                else:
                    logging.warning(f"Unknown message type from {drone_id}: {msg_type}")
        except WebSocketDisconnect:
            logging.info(f"Drone {drone_id} disconnected.")
        except asyncio.CancelledError:
            logging.info(f"Message receiver for {drone_id} cancelled.")
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON received from {drone_id}.")
        except Exception as e:
            logging.error(f"Error receiving from {drone_id}: {e}")

    consumer_task = None
    try:
        async with connection_pool.acquire() as connection:
            channel = await connection.channel()
            queue_name = f"{settings.QUEUE_COMMANDS_PREFIX}.{drone_id}"
            routing_key = f"drone.{drone_id}"
            
            command_queue = await channel.declare_queue(
                queue_name, durable=True, exclusive=False, auto_delete=False
            )
            await command_queue.bind(settings.EXCHANGE_COMMANDS, routing_key=routing_key)
            
            consumer_task = asyncio.create_task(consume_commands(command_queue))
            receiver_task = asyncio.create_task(receive_messages())
            
            await asyncio.gather(consumer_task, receiver_task)

    except Exception as e:
        logging.error(f"WebSocket handler for {drone_id} crashed: {e}")
    finally:
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()
        if command_queue:
            try:
                await command_queue.unbind(settings.EXCHANGE_COMMANDS)
            except Exception as e:
                logging.warning(f"Failed to unbind queue for {drone_id}: {e}")
        await connection_pool.close()
        logging.info(f"Cleaned up resources for {drone_id}.")
