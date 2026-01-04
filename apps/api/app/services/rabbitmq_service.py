# apps/api/app/services/rabbitmq_service.py

import aio_pika
import json
import logging
import asyncio
from app.core.config import get_core_settings, CoreSettings
from fastapi import Depends, HTTPException
from typing import Optional, Any, Dict
from aiormq.exceptions import AMQPConnectionError, AMQPError

logger = logging.getLogger("airdeliver.rabbitmq")

class RabbitMQService:
    """
    �� DIAMOND STANDARD RABBITMQ SERVICE (V32.0 - HIGH AVAILABILITY)
    Features:
    - Startup Probe: Waits up to 60s for RabbitMQ to become ready (Fixes ConnectionRefused).
    - Auto-Healing: Uses connect_robust for automatic reconnection.
    - Thread-Safe Singleton.
    """
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
        self._conn_lock = asyncio.Lock()

    async def connect(self):
        """Establishes connection with aggressive startup retries."""
        async with self._conn_lock:
            if self.connection and not self.connection.is_closed:
                return

            # 🛡️ STARTUP STRATEGY: Wait longer for RabbitMQ (it can be slow to boot)
            retries = 10  # Increased attempts
            base_delay = 2

            for attempt in range(retries):
                try:
                    logger.info(f"🐰 Connecting to RabbitMQ at {self.settings.RABBITMQ_HOST}... (Attempt {attempt + 1}/{retries})")
                    
                    # نستخدم connect_robust مباشرة هنا للتحكم في عملية المحاولة
                    self.connection = await aio_pika.connect_robust(
                        self.connection_uri,
                        timeout=60, # Long timeout for handshake
                        heartbeat=60,
                        client_properties={"connection_name": "airdeliver-backend-diamond"}
                    )
                    
                    self.channel = await self.connection.channel(publisher_confirms=True)
                    
                    self.exchange = await self.channel.declare_exchange(
                        self.exchange_name,
                        type=aio_pika.ExchangeType.TOPIC,
                        durable=True
                    )
                    
                    logger.info(f"✅ RabbitMQ Connected & Exchange '{self.exchange_name}' Ready.")
                    return

                except (OSError, AMQPError, asyncio.TimeoutError, ConnectionRefusedError) as e:
                    if attempt == retries - 1:
                        logger.critical(f"🔥 FATAL: RabbitMQ Unreachable after {retries} attempts. System Exiting. Error: {e}")
                        raise e
                    
                    # Log wait time
                    wait_time = min(base_delay * (1.5 ** attempt), 10) # Cap at 10s wait
                    logger.warning(f"⚠️ RabbitMQ not ready yet (Connection Refused). Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)

    async def close(self):
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("🛑 RabbitMQ Connection Closed Gracefully.")
        except Exception as e:
            logger.error(f"⚠️ Error closing RabbitMQ: {e}")

    async def publish(self, body: Dict[str, Any], routing_key: str, max_retries: int = 3):
        attempt = 0
        while attempt < max_retries:
            try:
                # Ensure connection is alive
                if not self.connection or self.connection.is_closed:
                    await self.connect()

                if not self.exchange:
                    # Try to recover topology
                    self.exchange = await self.channel.declare_exchange(
                        self.exchange_name, type=aio_pika.ExchangeType.TOPIC, durable=True
                    )

                try:
                    message_body = json.dumps(body, default=str)
                except (TypeError, ValueError) as e:
                    logger.error(f"❌ Logic Error: Cannot serialize payload. {e}")
                    raise e 
                
                message = aio_pika.Message(
                    body=message_body.encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    app_id="airdeliver-api"
                )
                
                confirmation = await self.exchange.publish(
                    message, 
                    routing_key=routing_key,
                    timeout=5.0
                )
                
                if confirmation: return True
                logger.warning(f"⚠️ NACK received for {routing_key}")

            except (AMQPError, asyncio.TimeoutError, ConnectionError, OSError) as e:
                attempt += 1
                logger.warning(f"⚠️ Publish failed (Attempt {attempt}/{max_retries}). Error: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * attempt)
                else:
                    logger.error(f"🔥 Publish Exhausted to '{routing_key}'.")

            except Exception as e:
                logger.critical(f"🔥 Unexpected Publish Error: {e}", exc_info=True)
                raise e
        
        return False # Fail silently to prevent worker crash loop

# --- SINGLETON ---
_rabbitmq_service_instance: Optional[RabbitMQService] = None
_init_lock = asyncio.Lock()

async def get_rabbitmq_service(
    settings: CoreSettings = Depends(get_core_settings),
) -> RabbitMQService:
    global _rabbitmq_service_instance
    if _rabbitmq_service_instance is None:
        async with _init_lock:
            if _rabbitmq_service_instance is None:
                service = RabbitMQService(settings)
                await service.connect()
                _rabbitmq_service_instance = service
    
    if _rabbitmq_service_instance.connection is None or _rabbitmq_service_instance.connection.is_closed:
        await _rabbitmq_service_instance.connect()
        
    return _rabbitmq_service_instance

# --- LIFECYCLE ---
async def init_rabbitmq():
    settings = get_core_settings()
    await get_rabbitmq_service(settings)

async def close_rabbitmq():
    global _rabbitmq_service_instance
    if _rabbitmq_service_instance:
        await _rabbitmq_service_instance.close()
        _rabbitmq_service_instance = None
