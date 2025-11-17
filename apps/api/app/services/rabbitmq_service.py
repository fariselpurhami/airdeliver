# apps/api/app/services/rabbitmq_service.py

import aio_pika
import json
import logging
from app.core.config import get_core_settings, CoreSettings
from fastapi import Depends, HTTPException
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class RabbitMQService:
    def __init__(self, settings: CoreSettings):
        self.settings = settings
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.exchange: Optional[aio_pika.abc.AbstractExchange] = None
        self.exchange_name = "airdeliver_main_exchange"
        
        self.connection_uri = (
            f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASS}"
            f"@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}/"
        )

    async def connect(self):
        if self.connection and not self.connection.is_closed:
            return

        try:
            TIMEOUT_SECONDS = 5 

            self.connection = await aio_pika.connect_robust(
                self.connection_uri,
                timeout=TIMEOUT_SECONDS
            )
            self.channel = await self.connection.channel()
            
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            logger.info(f"Successfully connected to RabbitMQ ({self.settings.RABBITMQ_HOST}) and declared exchange '{self.exchange_name}'")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ using URI: {self.connection_uri}: {e}", exc_info=True)
            raise

    async def close(self):
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("RabbitMQ connection closed.")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}", exc_info=True)

    async def publish(self, body: Dict[str, Any], routing_key: str):
        if not self.connection or self.connection.is_closed:
            logger.warning("RabbitMQ connection lost. Reconnecting...")
            await self.connect()

        if not self.channel or not self.exchange:
            logger.error("RabbitMQ channel or exchange not available. Cannot publish.")
            raise HTTPException(status_code=503, detail="Messaging service unavailable")

        try:
            message_body = json.dumps(body, default=str)
            message = aio_pika.Message(
                body=message_body.encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await self.exchange.publish(message, routing_key=routing_key)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to serialize message body: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to publish message to {routing_key}: {e}", exc_info=True)


_rabbitmq_service_instance: Optional[RabbitMQService] = None

async def get_rabbitmq_service(
    settings: CoreSettings = Depends(get_core_settings),
) -> RabbitMQService:
    global _rabbitmq_service_instance
    
    if _rabbitmq_service_instance is None:
        _rabbitmq_service_instance = RabbitMQService(settings)
        await _rabbitmq_service_instance.connect()
        
    if _rabbitmq_service_instance.connection is None or _rabbitmq_service_instance.connection.is_closed:
        await _rabbitmq_service_instance.connect()
        
    return _rabbitmq_service_instance
