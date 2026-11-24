import asyncio,threading,time
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import numpy as np
import pytest
from app.services.ai_commerce_engine import AICommerceEngine,EngineLimits,PRODUCT_TEXT_MODEL,SearchResult
from app.services.query_vector_cache import QueryVectorCache
from tests.test_embedding_admission import SlowEncoder,engine

def test_vector_cache_bound_ttl_identity_and_copy(monkeypatch):
    cache=QueryVectorCache(capacity=2,ttl=10)
    clock=[1.];monkeypatch.setattr('app.services.query_vector_cache.time.monotonic',lambda:clock[0])
    cache.put(('gte','q'),[1,0],2);v=cache.get(('gte','q'));v[0]=99
    assert cache.get(('gte','q'))==[1,0] and cache.get(('granite','q')) is None
    cache.put('bad',[float('nan'),0],2);assert cache.get('bad') is None
    cache.put('b',[0,1],2);cache.put('c',[0,1],2);assert cache.get(('gte','q')) is None
    clock[0]=12.;assert cache.get('b') is None

@pytest.mark.asyncio
async def test_late_completed_vector_cached_without_extra_native_call():
    model=SlowEncoder();svc=engine(model,.02)
    try:
        with pytest.raises(Exception):await svc.get_query_embedding('same query')
    finally:model.release.set();await asyncio.sleep(.05)
    v=await svc.get_query_embedding('same query');assert len(v)==PRODUCT_TEXT_MODEL.dimension and model.calls==1
    v[0]=999
    assert (await svc.get_query_embedding('same query'))[0]==1

@pytest.mark.asyncio
async def test_real_hybrid_keyword_starts_before_embedding_and_survives_timeout(monkeypatch):
    from app.services import ai_commerce_engine as module
    monkeypatch.setattr(module,'get_core_settings',lambda:SimpleNamespace(SEARCH_EMBEDDING_BUDGET_SECONDS=.025))
    model=SlowEncoder();svc=engine(model,1);svc.bootstrap=AsyncMock()
    keyword_started=threading.Event();milvus=AsyncMock(return_value=[])
    svc._search_milvus_text=milvus
    async def keyword(*args):
        keyword_started.set();return []
    svc._search_opensearch=keyword
    marker=SimpleNamespace(id=4)
    svc._fallback_sql_search=AsyncMock(return_value=[marker])
    started=time.monotonic()
    try:
        result=await svc.perform_hybrid_search_pure(None,'query',limit=5)
        assert keyword_started.is_set() and model.started.is_set()
        assert time.monotonic()-started<.3 and result==[marker]
        milvus.assert_not_awaited()
        # A second cold query does not overlap still-running native work.
        await svc.perform_hybrid_search_pure(None,'different',limit=5)
        assert model.calls==1 and model.maximum==1
    finally:model.release.set();await asyncio.sleep(.05)
