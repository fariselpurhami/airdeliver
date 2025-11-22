# apps/api/app/services/rabbitmq_service.py

import aio_pika
import json
import logging
import asyncio
from app.core.config import get_core_settings, CoreSettings
from fastapi import Depends, HTTPException
from typing import Optional, Any, Dict
from aiormq.exceptions import AMQPConnectionError

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
        self._lock = asyncio.Lock()

    async def connect(self):
        async with self._lock:
            if self.connection and not self.connection.is_closed:
                return

            retries = 10
            base_delay = 2

            for attempt in range(retries):
                try:
                    logger.info(f"Connecting to RabbitMQ at {self.settings.RABBITMQ_HOST}... (Attempt {attempt + 1}/{retries})")
                    
                    self.connection = await aio_pika.connect_robust(
                        self.connection_uri,
                        timeout=10,
                        client_properties={"connection_name": "airdeliver-backend-service"}
                    )
                    
                    self.channel = await self.connection.channel(publisher_confirms=True)
                    
                    self.exchange = await self.channel.declare_exchange(
                        self.exchange_name,
                        type=aio_pika.ExchangeType.TOPIC,
                        durable=True
                    )
                    
                    logger.info(f"✅ Connected to RabbitMQ & Exchange '{self.exchange_name}' ready.")
                    return

                except (OSError, AMQPConnectionError, asyncio.TimeoutError) as e:
                    if attempt == retries - 1:
                        logger.critical(f"🔥 Exhausted all retries connecting to RabbitMQ: {e}", exc_info=True)
                        raise
                    
                    wait_time = base_delay * (attempt + 1)
                    logger.warning(f"⚠️ Connection failed ({e}). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    logger.critical(f"🔥 Unexpected error connecting to RabbitMQ: {e}", exc_info=True)
                    raise

    async def close(self):
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("RabbitMQ connection closed gracefully.")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}", exc_info=True)

    async def publish(self, body: Dict[str, Any], routing_key: str):
        if not self.connection or self.connection.is_closed:
            logger.warning("RabbitMQ connection lost. Attempting strict reconnect...")
            await self.connect()

        if not self.channel or not self.exchange:
            logger.error("RabbitMQ channel/exchange unavailable after reconnect attempt.")
            raise HTTPException(status_code=503, detail="Messaging infrastructure unavailable")

        try:
            message_body = json.dumps(body, default=str)
            
            message = aio_pika.Message(
                body=message_body.encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                app_id="airdeliver-api",
                timestamp=None
            )
            
            confirmation = await self.exchange.publish(
                message, 
                routing_key=routing_key,
                timeout=5.0
            )
            
            if not confirmation:
                logger.error(f"Message to {routing_key} was NOT confirmed by broker (NACK).")

        except json.JSONDecodeError as e:
            logger.error(f"Serialization Error: {e}", exc_info=True)
        except aio_pika.exceptions.UnroutableError:
             logger.error(f"Message returned: No queue bound to {routing_key}")
        except Exception as e:
            logger.error(f"Critical Publish Error to {routing_key}: {e}", exc_info=True)

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
