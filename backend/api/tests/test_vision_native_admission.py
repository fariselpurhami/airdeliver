import asyncio
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import torch
from PIL import Image
from app.services.ai_commerce_engine import AICommerceEngine,EngineLimits,ExternalDependencyError,PRODUCT_VISION_MODEL
import app.services.ai_commerce_engine as module


class BlockingVision:
    def __init__(self):
        self.started=threading.Event();self.release=threading.Event();self.calls=0
    def parameters(self):return iter([torch.zeros(1)])
    def get_image_features(self,**inputs):
        self.calls+=1;self.started.set();self.release.wait(2)
        return torch.ones((1,PRODUCT_VISION_MODEL.dimension))


def engine(timeout=.04):
    return AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object(),
        limits=replace(EngineLimits(),vector_search_timeout_seconds=timeout))


@pytest.fixture
def setup(monkeypatch):
    gate=threading.BoundedSemaphore(1);monkeypatch.setattr(module,'_VISION_NATIVE_GATE',gate)
    model=BlockingVision()
    monkeypatch.setattr(module.model_registry,'get_vision_stack',lambda:(model,lambda **kw:{}))
    monkeypatch.setattr(AICommerceEngine,'_decode_image_bounded',lambda self,value:Image.new('RGB',(2,2)))
    return model,gate


@pytest.mark.asyncio
async def test_timeout_keeps_shared_vision_slot_until_native_work_finishes(setup):
    model,gate=setup
    try:
        with pytest.raises(ExternalDependencyError):await engine()._encode_image_to_vector('image')
        assert model.started.is_set()
        with pytest.raises(ExternalDependencyError):await engine()._encode_image_to_vector('other')
        assert model.calls==1
    finally:model.release.set();await asyncio.sleep(.05)
    assert len(await engine(1)._encode_image_to_vector('third'))==PRODUCT_VISION_MODEL.dimension


@pytest.mark.asyncio
async def test_cancellation_does_not_release_running_native_slot(setup):
    model,gate=setup
    task=asyncio.create_task(engine(1)._encode_image_to_vector('image'))
    for _ in range(100):
        if model.started.is_set():break
        await asyncio.sleep(.002)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    try:
        with pytest.raises(ExternalDependencyError):await engine()._encode_image_to_vector('other')
        assert model.calls==1
    finally:model.release.set();await asyncio.sleep(.05)


@pytest.mark.asyncio
async def test_decode_runs_off_event_loop_and_failure_releases_slot(monkeypatch):
    gate=threading.BoundedSemaphore(1);monkeypatch.setattr(module,'_VISION_NATIVE_GATE',gate)
    caller=threading.get_ident();threads=[]
    def decode(self,value):
        threads.append(threading.get_ident());raise ValueError('invalid image')
    monkeypatch.setattr(AICommerceEngine,'_decode_image_bounded',decode)
    for _ in range(2):
        # This test checks thread placement and exception/slot cleanup, not40ms
        # scheduling on a loaded CI worker. Deadline behavior is tested above.
        with pytest.raises(ValueError):await engine(1)._encode_image_to_vector('bad')
    assert len(threads)==2 and all(t!=caller for t in threads)
    assert gate.acquire(blocking=False)
    gate.release()
