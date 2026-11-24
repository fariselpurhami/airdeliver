"""Syntactically complete output can still be incomplete at the provider seam."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import StructuredOutputError
from app.services.ai_nlu_service import GlobalCommerceIntentEngine,AINLUService
from tests.test_llm_execution_limits import service


def response(text,finish='length'):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,message=SimpleNamespace(content=text))])

@pytest.mark.asyncio
@pytest.mark.parametrize('json_mode',[True,False])
async def test_actual_strict_adapter_rejects_length_even_when_body_parses(json_mode):
    llm=service();llm._chat_completion=AsyncMock(return_value=response('{}' if json_mode else 'Partial reply'))
    with pytest.raises(StructuredOutputError):
        await llm.generate_response_strict(prompt='customer input',json_mode=json_mode)
    assert 'raise_on_failure' not in llm._chat_completion.await_args.kwargs

@pytest.mark.asyncio
async def test_legacy_non_strict_contract_is_unchanged():
    llm=service();llm._chat_completion=AsyncMock(return_value=response('Legacy partial reply'))
    assert await llm.generate_response(prompt='customer input')=='Legacy partial reply'
    llm._chat_completion.return_value=response('Complete reply','stop')
    assert await llm.generate_response_strict(prompt='customer input')=='Complete reply'

@pytest.mark.asyncio
async def test_global_intent_cannot_accept_valid_but_truncated_partial_target_list():
    llm=service();llm._chat_completion=AsyncMock(return_value=response(json.dumps({'category':'SPECIFIC_SEARCH','is_chitchat':False,'target_products':[{'product_name':'Atlas chair'}]})))
    result=await GlobalCommerceIntentEngine(llm).analyze_intent('Atlas chair and Atlas laptop')
    assert result.target_products==[] and result.cart_action_type is None

@pytest.mark.asyncio
async def test_query_optimizer_retains_customer_query_after_truncated_rewrite():
    llm=service();llm._chat_completion=AsyncMock(return_value=response('chair'))
    svc=object.__new__(AINLUService);svc.llm_service=llm
    assert await svc._optimize_search_query('chair without red')=='chair without red'
