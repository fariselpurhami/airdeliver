import asyncio
import threading
import time
from dataclasses import replace
import numpy as np
import pytest
from app.services.ai_commerce_engine import AICommerceEngine,EngineLimits,ExternalDependencyError,PRODUCT_TEXT_MODEL

class SlowEncoder:
    def __init__(self):
        self.started=threading.Event();self.release=threading.Event();self.active=0;self.maximum=0;self.calls=0
    def encode(self,*args,**kwargs):
        self.calls+=1;self.active+=1;self.maximum=max(self.maximum,self.active);self.started.set()
        try:
            self.release.wait(2)
            return np.ones(PRODUCT_TEXT_MODEL.dimension)
        finally:self.active-=1

def engine(model,timeout=.04):
    return AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=model,limits=replace(EngineLimits(),embedding_timeout_seconds=timeout))

@pytest.mark.asyncio
async def test_timed_out_thread_keeps_shared_model_slot_until_it_really_finishes():
    model=SlowEncoder();first=engine(model);second=engine(model)
    try:
        with pytest.raises(ExternalDependencyError):await first.get_query_embedding('one')
        assert model.started.is_set()
        with pytest.raises(ExternalDependencyError):await second.get_query_embedding('two')
        assert model.calls==1 and model.maximum==1
    finally:
        model.release.set();await asyncio.sleep(.05)
    assert len(await second.get_query_embedding('three'))==PRODUCT_TEXT_MODEL.dimension

@pytest.mark.asyncio
async def test_cancellation_does_not_release_running_thread_early():
    model=SlowEncoder();first=engine(model,1);second=engine(model)
    task=asyncio.create_task(first.get_query_embedding('one'))
    for _ in range(100):
        if model.started.is_set():break
        await asyncio.sleep(.002)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    try:
        with pytest.raises(ExternalDependencyError):await second.get_query_embedding('two')
        assert model.calls==1
    finally:model.release.set();await asyncio.sleep(.05)
