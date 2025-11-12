# apps/api/app/services/rabbitmq_service.py

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
        logging.info("API connecting to RabbitMQ...")
        
        async def get_connection() -> AbstractRobustConnection:
            return await aio_pika.connect_robust(settings.RABBITMQ_URL)
        
        self.connection_pool = Pool(get_connection, max_size=5)

        async def get_channel() -> aio_pika.Channel:
            async with self.connection_pool.acquire() as connection:
                return await connection.channel()

        self.channel_pool = Pool(get_channel, max_size=20)
        
        async with self.channel_pool.acquire() as channel:
            await channel.set_qos(prefetch_count=10)

            await channel.declare_exchange(
                settings.EXCHANGE_TELEMETRY, aio_pika.ExchangeType.TOPIC, durable=True
            )
            await channel.declare_exchange(
                settings.EXCHANGE_EVENTS, aio_pika.ExchangeType.TOPIC, durable=True
            )
            await channel.declare_exchange(
                settings.EXCHANGE_COMMANDS, aio_pika.ExchangeType.TOPIC, durable=True
            )

            await channel.declare_queue(settings.QUEUE_TELEMETRY, durable=True)
            await channel.declare_queue(settings.QUEUE_EVENTS, durable=True)
        
        logging.info("API RabbitMQ connection and exchanges/queues declared.")

    async def disconnect(self):
        if self.channel_pool:
            await self.channel_pool.close()
        if self.connection_pool:
            await self.connection_pool.close()
        logging.info("API RabbitMQ pools closed.")

    async def publish_command(self, routing_key: str, message_body: bytes):
        if not self.channel_pool:
            raise ConnectionError("RabbitMQ channel pool is not initialized.")
            
        async with self.channel_pool.acquire() as channel:
            message = aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            exchange = await channel.get_exchange(settings.EXCHANGE_COMMANDS)
            await exchange.publish(message, routing_key=routing_key)

rabbitmq_service = RabbitMQService()
