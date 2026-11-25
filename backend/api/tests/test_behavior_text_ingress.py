"""Invalid behavior text never reaches native encoder or inference buffer."""
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import logging
import pytest
from app.services.ai_behavior_engine import BehaviorEngine

@pytest.mark.asyncio
@pytest.mark.parametrize('uid,text,weight',[
 (True,'audio',1),('7','audio',1),(0,'audio',1),(2147483648,'audio',1),
 (7,123,1),(7,None,1),(7,'',1),(7,' '*3,1),(7,'x'*4001,1),
 (7,'audio',True),(7,'audio','1'),(7,'audio',float('nan')),(7,'audio',float('inf')),(7,'audio',0),(7,'audio',-1),
])
async def test_invalid_behavior_seam_values_stop_before_registry(monkeypatch,uid,text,weight):
    registry=Mock(side_effect=AssertionError('No model call'))
    monkeypatch.setattr('app.services.ai_commerce_engine.ModelRegistry',registry)
    engine=object.__new__(BehaviorEngine);engine.track_interaction=AsyncMock()
    await engine.register_interaction(uid,text,weight)
    registry.assert_not_called();engine.track_interaction.assert_not_awaited()

@pytest.mark.asyncio
async def test_model_failure_log_does_not_include_private_signal_or_exception(monkeypatch,caplog):
    registry=Mock(side_effect=RuntimeError('PRIVATE_SIGNAL_OR_MODEL_CREDENTIAL'))
    monkeypatch.setattr('app.services.ai_commerce_engine.ModelRegistry',registry)
    engine=object.__new__(BehaviorEngine);engine.track_interaction=AsyncMock()
    with caplog.at_level(logging.WARNING):await engine.register_interaction(7,'PRIVATE_CUSTOMER_QUERY')
    assert 'PRIVATE_' not in caplog.text
    engine.track_interaction.assert_not_awaited()
