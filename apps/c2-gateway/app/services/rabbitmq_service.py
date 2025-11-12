# apps/c2-gateway/app/services/rabbitmq_service.py

import aio_pika
import logging
from aio_pika.abc import AbstractRobustConnection
from aio_pika.pool import Pool
from app.core.config import settings

class RabbitMQService:
    def __init__(self):
        self.connection_pool = None
        self.channel_pool = None

    async def connect(self):
        logging.info("C2-Gateway: Connecting to RabbitMQ...")
        
        async def get_connection() -> AbstractRobustConnection:
            return await aio_pika.connect_robust(settings.RABBITMQ_URL)
        
        self.connection_pool = Pool(get_connection, max_size=5)

        async def get_channel() -> aio_pika.Channel:
            async with self.connection_pool.acquire() as connection:
                return await connection.channel()

        self.channel_pool = Pool(get_channel, max_size=20)
        
        async with self.channel_pool.acquire() as channel:
            await channel.declare_exchange(
                settings.EXCHANGE_TELEMETRY, aio_pika.ExchangeType.TOPIC, durable=True
            )
            await channel.declare_exchange(
                settings.EXCHANGE_EVENTS, aio_pika.ExchangeType.TOPIC, durable=True
            )
            await channel.declare_exchange(
                settings.EXCHANGE_COMMANDS, aio_pika.ExchangeType.TOPIC, durable=True
            )
        logging.info("C2-Gateway: RabbitMQ connection and exchanges declared.")

    async def disconnect(self):
        if self.channel_pool:
            await self.channel_pool.close()
        if self.connection_pool:
            await self.connection_pool.close()
        logging.info("C2-Gateway: RabbitMQ pools closed.")

    async def publish_message(self, exchange_name: str, routing_key: str, message_body: bytes):
        if not self.channel_pool:
            raise ConnectionError("RabbitMQ channel pool is not initialized.")
            
        async with self.channel_pool.acquire() as channel:
            message = aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            exchange = await channel.get_exchange(exchange_name)
            await exchange.publish(message, routing_key=routing_key)

rabbitmq_service = RabbitMQService()
