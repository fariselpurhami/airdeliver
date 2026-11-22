import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_voice_service import VoiceToolExecutor


@pytest.mark.asyncio
@pytest.mark.parametrize('accepted',[True,False])
async def test_voice_cart_reports_only_confirmed_queue_admission_not_execution(accepted):
    broker=SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=accepted)))
    executor=VoiceToolExecutor(object(),object(),broker,object(),object())
    result=json.loads(await executor.execute_cart_action({'action':'ADD','product_id':5},'1',object()))
    assert result['status']==('QUEUED' if accepted else 'FAILED')
    assert 'action_executed' not in result
