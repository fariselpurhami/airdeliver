"""Invalid telemetry must not stage vectors or mutate Redis histories."""
import asyncio,logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_behavior_engine import BehaviorEngine

@pytest.mark.asyncio
@pytest.mark.parametrize('uid,metadata',[
 (True,{'id':1}),(0,{'id':1}),(-1,{'id':1}),('7',{'id':1}),
 (7,{'id':True}),(7,{'id':-1}),(7,{'id':'1'}),
 (7,{'price':float('nan')}),(7,{'price':float('inf')}),(7,{'price':-1}),
 (7,{'vec':[float('nan')]}),(7,{'vec':[float('inf')]}),(7,{'vec':[True]}),
 (7,{'vec':['0.1']}),(7,{'vec':[0.1]*4097}),(7,{'vec':[]}),
 (7,{'image_vector':[float('nan')]}),
 (7,None),(7,[]),
])
async def test_invalid_telemetry_never_queues_or_starts_history_updates(uid,metadata,caplog):
    engine=object.__new__(BehaviorEngine);engine._background_tasks=set();engine.synaptic_buffer=asyncio.Queue()
    engine._update_price_history=AsyncMock();engine._update_seen_history=AsyncMock()
    with caplog.at_level(logging.WARNING):await engine.track_interaction(uid,'view',metadata)
    assert engine.synaptic_buffer.empty() and not engine._background_tasks
    engine._update_price_history.assert_not_awaited();engine._update_seen_history.assert_not_awaited()
    assert 'PRIVATE_SENTINEL' not in caplog.text

@pytest.mark.asyncio
async def test_valid_same_source_vector_keeps_existing_staging_contract():
    engine=object.__new__(BehaviorEngine);engine._background_tasks=set();engine.synaptic_buffer=asyncio.Queue()
    engine.net_config=SimpleNamespace(supported_dims={'dim_384':384});engine.embedding_sources={'dim_384':'test-source'}
    engine._update_price_history=AsyncMock();engine._update_seen_history=AsyncMock()
    await engine.track_interaction(7,'view',{'id':1,'price':0.0,'vec':[0.1]*384,'action':'add'})
    packet=engine.synaptic_buffer.get_nowait()
    assert packet['u']==7 and packet['item_id']==1 and packet['price']==0 and packet['d']==384
    await asyncio.gather(*list(engine._background_tasks))
    engine._update_price_history.assert_awaited_once_with(7,0.0);engine._update_seen_history.assert_awaited_once_with(7,1)
