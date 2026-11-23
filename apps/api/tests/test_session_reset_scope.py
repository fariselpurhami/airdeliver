from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService,InternalCommand


@pytest.mark.asyncio
async def test_session_reset_never_claims_persistent_memory_or_orders_erased():
    svc=AINLUService(object(),object(),SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=True))),SimpleNamespace(delete=AsyncMock()),object())
    svc._safe_send_ui=AsyncMock()
    await svc._process_internal_command(17,InternalCommand.RESET_SESSION.value)
    body=svc._safe_send_ui.call_args.args[1]['content']
    assert 'preferences are unchanged and order records are not erased' in body
    assert 'may cancel pending orders' in body
    assert 'memory cleared' not in body
    assert 'requested' in body
    keys=[call.args[0] for call in svc.cache.delete.call_args_list]
    assert all('customer_memory' not in key for key in keys)
