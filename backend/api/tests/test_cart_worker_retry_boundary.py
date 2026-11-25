"""An uncertain cart write must not enter generic mutation replay."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.services.ai_cart_service import CartPersistenceError
from app.services.orchestration.worker_entrypoint import WorkerRuntime


class Context:
    async def __aenter__(self):return self
    async def __aexit__(self,*args):return False


def message():
    return SimpleNamespace(body=json.dumps({'user_id':1,'product_id':7}).encode(),
        headers={},routing_key='airdeliver.ai.cart.add',process=lambda **kwargs:Context(),
        ack=AsyncMock(),reject=AsyncMock())


@pytest.mark.asyncio
@pytest.mark.parametrize('notification_fails',[False,True])
async def test_unconfirmed_cart_write_is_not_republished(notification_fails):
    runtime=WorkerRuntime()
    runtime.services.cache=SimpleNamespace(publish=AsyncMock(side_effect=ConnectionError('offline') if notification_fails else None))
    runtime.republish_with_headers=AsyncMock()
    handler=AsyncMock(side_effect=CartPersistenceError('write response lost'))
    incoming=message()
    await runtime.smart_retry_wrapper(incoming,handler)
    handler.assert_awaited_once()
    runtime.republish_with_headers.assert_not_awaited()
    incoming.reject.assert_awaited_once_with(requeue=False)
    incoming.ack.assert_not_awaited()
    args=runtime.services.cache.publish.await_args.args
    assert args[0]=='airdeliver:response:1'
    notification=json.loads(args[1])
    assert notification['type']=='error' and 'Refresh' in notification['content']


@pytest.mark.asyncio
async def test_other_transient_work_retains_existing_retry_policy(monkeypatch):
    from app.services.orchestration import worker_entrypoint as worker
    runtime=WorkerRuntime();runtime.republish_with_headers=AsyncMock()
    incoming=message();handler=AsyncMock(side_effect=ConnectionError('temporary'))
    monkeypatch.setattr(worker.asyncio,'sleep',AsyncMock())
    await runtime.smart_retry_wrapper(incoming,handler)
    runtime.republish_with_headers.assert_awaited_once()
    incoming.ack.assert_awaited_once()
    incoming.reject.assert_not_awaited()


from tests.test_cart_persistence_outcomes import real_cache
from tests.test_ai_cart_service import FakeDB, make_product
from app.services.ai_cart_service import AICartService


@pytest.mark.asyncio
async def test_real_redis_write_commits_but_response_lost_never_replays_add(real_cache):
    cache,_=real_cache
    runtime=WorkerRuntime();runtime.services.cache=cache
    runtime.republish_with_headers=AsyncMock()
    original=cache.compare_json_required
    async def lost_response(*args,**kwargs):
        assert await original(*args,**kwargs) is True
        raise ConnectionError('reply lost after redis transaction committed')
    cache.compare_json_required=lost_response
    service=AICartService(FakeDB(make_product()),cache,object())
    handler=AsyncMock(side_effect=service.handle_add_to_cart)
    incoming=message()
    await runtime.smart_retry_wrapper(incoming,handler)
    stored=await cache.get_json_required('ai_cart:1')
    assert stored['items'][0]['quantity']==1
    handler.assert_awaited_once()
    runtime.republish_with_headers.assert_not_awaited()
    incoming.reject.assert_awaited_once_with(requeue=False)


@pytest.mark.asyncio
async def test_broker_message_id_becomes_stable_mutation_id_across_delivery():
    runtime=WorkerRuntime()
    received=[]
    async def handler(payload):received.append(payload)
    for _ in range(2):
        incoming=message();incoming.message_id='publisher-stable-message'
        await runtime.smart_retry_wrapper(incoming,handler)
    assert received[0]['mutation_id']==received[1]['mutation_id']
    from uuid import UUID
    UUID(received[0]['mutation_id'])
