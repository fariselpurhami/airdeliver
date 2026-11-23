"""Real AMQP confirmed publish/delivery and read-only worker execution.

Run only against the dedicated disposable CI broker, never a user broker.
"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import aio_pika
import pytest
from app.core.config import CoreSettings
from app.schemas.cart_recommendation import CART_RECOMMENDATION_ROUTING_KEY
from app.services.rabbitmq_service import RabbitMQService,EXCHANGE_NAME
from app.services.ai_cart_service import AICartService
from worker_entrypoint import WorkerRuntime
from tests.test_ai_cart_service import FakeDB,FakeCache,make_product


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv('TEST_RABBITMQ_DISPOSABLE')!='1',reason='dedicated disposable RabbitMQ required')
async def test_real_amqp_readonly_followup_confirms_delivers_and_never_replays_cart():
    settings=CoreSettings(RABBITMQ_HOST='127.0.0.1',RABBITMQ_PORT=int(os.getenv('TEST_RABBITMQ_PORT','5672')),RABBITMQ_USER='airdeliver_ci',RABBITMQ_PASS='disposable-ci-only')
    connection=await aio_pika.connect_robust(settings.RABBITMQ_URL)
    broker=RabbitMQService(settings)
    channel=await connection.channel()
    exchange=await channel.declare_exchange(EXCHANGE_NAME,aio_pika.ExchangeType.TOPIC,durable=True)
    queue=await channel.declare_queue('airdeliver-ci-cart-'+uuid4().hex,durable=True,arguments={'x-queue-type':'quorum'})
    await queue.bind(exchange,routing_key=CART_RECOMMENDATION_ROUTING_KEY)
    cache=FakeCache()
    product=SimpleNamespace(model_dump=lambda **kw:{'id':8,'name':'Actual catalog candidate','price':'12.00'})
    engine=SimpleNamespace(generate_perfect_bundle=AsyncMock(return_value=[product]))
    @asynccontextmanager
    async def session():yield FakeDB(make_product())
    runtime=WorkerRuntime.__new__(WorkerRuntime)
    runtime.wait_for_readiness=AsyncMock()
    runtime.services=SimpleNamespace(session_maker=session,cache=cache,rabbitmq=broker,commerce=engine)
    try:
        await broker.connect()
        producer=AICartService(FakeDB(make_product()),cache,broker)
        await producer.handle_add_to_cart({'user_id':17,'product_id':7})
        async with asyncio.timeout(5):
            message=None
            while message is None:
                message=await queue.get(fail=False)
                if message is None:await asyncio.sleep(.02)
        payload=json.loads(message.body)
        assert payload=={'version':1,'user_id':17,'product_id':7,'operation':'added'}
        assert message.delivery_mode==aio_pika.DeliveryMode.PERSISTENT
        sets_before=len(cache.sets)
        async with message.process():await runtime.cart_recommendation_handler_impl(payload)
        assert len(cache.sets)==sets_before and cache.deleted==[]
        carousels=[p for _,p in cache.published if p.get('type')=='product_carousel']
        assert carousels[-1]['products'][0]['id']==8
        assert cache._cart['items'][0]['quantity']==1
    finally:
        await queue.delete(if_unused=False,if_empty=False)
        await broker.close()
        await connection.close()
