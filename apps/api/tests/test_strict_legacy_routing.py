import asyncio,json,logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import GlobalCommerceIntentEngine,AINLUService
from tests.test_llm_execution_limits import service,completion

@pytest.mark.asyncio
async def test_global_router_uses_actual_strict_adapter_and_preserves_safe_failure_fallback(caplog):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(json.dumps({'category':'SPECIFIC_SEARCH','is_chitchat':False,'target_products':[{'product_name':'laptop'}]})))
    engine=GlobalCommerceIntentEngine(llm)
    result=await engine.analyze_intent('laptop')
    assert result.target_products[0].product_name=='laptop'
    llm._chat_completion=AsyncMock(side_effect=ConnectionError('private failure sentinel'))
    with caplog.at_level(logging.ERROR):result=await engine.analyze_intent('private customer sentinel laptop')
    assert result.cart_action_type is None and result.target_products==[]
    assert 'private failure sentinel' not in caplog.text and 'private customer sentinel' not in caplog.text
    llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):await engine.analyze_intent('laptop')

@pytest.mark.asyncio
async def test_query_optimizer_strict_failure_keeps_original_query_and_cancellation():
    llm=service();svc=AINLUService.__new__(AINLUService);svc.llm_service=llm
    llm._chat_completion=AsyncMock(return_value=completion('laptop'))
    assert await svc._optimize_search_query('show me a laptop please')=='laptop'
    llm._chat_completion=AsyncMock(side_effect=ConnectionError('private sentinel'))
    assert await svc._optimize_search_query('show me a laptop please')=='show me a laptop please'
    llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):await svc._optimize_search_query('show me a laptop please')

@pytest.mark.asyncio
async def test_older_injected_adapter_remains_supported_without_changing_voice_cart():
    llm=SimpleNamespace(generate_response=AsyncMock(return_value='laptop'))
    svc=AINLUService.__new__(AINLUService);svc.llm_service=llm
    assert await svc._optimize_search_query('show me a laptop please')=='laptop'
    llm.generate_response.assert_awaited_once()
