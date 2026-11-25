import asyncio
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_commerce_engine import AICommerceEngine,EngineLimits,SearchFilter,PRODUCT_TEXT_MODEL,PRODUCT_VISION_MODEL
import app.services.ai_commerce_engine as module


class BlockingSearch:
    def __init__(self):
        self.started=threading.Event();self.release=threading.Event();self.calls=[]
    def search(self,**kwargs):
        self.calls.append(kwargs);self.started.set();self.release.wait(2)
        return [[{'entity':{'id':17},'distance':.8}]]


def engine(client,timeout=.04):
    value=AICommerceEngine(opensearch_client=object(),milvus_client=client,embedding_model=object(),
        limits=replace(EngineLimits(),vector_search_timeout_seconds=timeout))
    value._bootstrapped=True
    value._fetch_products_by_ids=AsyncMock(return_value=['current-product'])
    return value


@pytest.fixture
def setup(monkeypatch):
    gate=threading.BoundedSemaphore(1);monkeypatch.setattr(module,'_VECTOR_NATIVE_GATE',gate)
    return BlockingSearch(),gate


@pytest.mark.asyncio
async def test_text_timeout_retains_shared_native_slot_for_visual_caller(setup):
    client,gate=setup;first=engine(client);second=engine(client)
    try:
        with pytest.raises(TimeoutError):
            await first._search_milvus_text([0.]*PRODUCT_TEXT_MODEL.dimension,5,SearchFilter())
        assert client.started.is_set()
        assert await second.search_by_image_vector([0.]*PRODUCT_VISION_MODEL.dimension)==[]
        assert len(client.calls)==1
        assert 0<client.calls[0]['timeout']<=.04
    finally:client.release.set();await asyncio.sleep(.05)
    assert await second.search_by_image_vector([0.]*PRODUCT_VISION_MODEL.dimension)==['current-product']
    assert len(client.calls)==2 and 'timeout' in client.calls[-1]


@pytest.mark.asyncio
async def test_cancelled_search_does_not_release_native_slot(setup):
    client,gate=setup
    task=asyncio.create_task(engine(client,1)._search_milvus_text([0.]*PRODUCT_TEXT_MODEL.dimension,5,SearchFilter()))
    for _ in range(100):
        if client.started.is_set():break
        await asyncio.sleep(.002)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    try:
        with pytest.raises(TimeoutError):await engine(client)._run_vector_native(client.search)
        assert len(client.calls)==1
    finally:client.release.set();await asyncio.sleep(.05)


@pytest.mark.asyncio
async def test_native_failure_releases_gate_and_waiter_never_submits_after_cancel(setup):
    client,gate=setup
    def fail(**kw):raise RuntimeError('controlled native failure')
    with pytest.raises(RuntimeError):await engine(client)._run_vector_native(fail)
    assert gate.acquire(blocking=False)
    task=asyncio.create_task(engine(client,1)._run_vector_native(client.search))
    await asyncio.sleep(.02);task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    gate.release()
    assert client.calls==[] and gate.acquire(blocking=False)
    gate.release()
