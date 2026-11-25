"""Actual adapter/SQL boundaries, no provider requests or category expansion."""
import asyncio,json,logging
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import StructuredOutputError
from app.services.customer_memory_service import CustomerMemoryService
from tests.test_llm_execution_limits import service,completion

@pytest.mark.asyncio
@pytest.mark.parametrize('payload',[{}, {'category':'color','value':'blue','evidence':'I prefer blue'}])
async def test_actual_strict_extractor_preserves_valid_empty_and_candidate(payload):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(json.dumps(payload)))
    assert await llm.extract_shopping_preferences('I prefer blue')==payload
    call=llm._chat_completion.await_args.kwargs
    assert call['max_tokens']==180 and call['response_format']=={'type':'json_object'}

@pytest.mark.asyncio
@pytest.mark.parametrize('raw',['','not JSON','[]','null','"private-output"'])
async def test_invalid_completion_is_not_valid_no_preference(raw):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(raw))
    with pytest.raises(StructuredOutputError):await llm.extract_shopping_preferences('I prefer blue')

@pytest.mark.asyncio
async def test_provider_failure_and_cancel_remain_distinct_and_private(caplog):
    llm=service();llm._chat_completion=AsyncMock(side_effect=ConnectionError('private-provider-sentinel'))
    with caplog.at_level(logging.ERROR),pytest.raises(Exception):
        await llm.extract_shopping_preferences('I prefer private-customer-sentinel blue')
    assert 'private-provider-sentinel' not in caplog.text and 'private-customer-sentinel' not in caplog.text
    llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):await llm.extract_shopping_preferences('I prefer blue')

from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['failure','empty','candidate','cancel'])
async def test_actual_strict_adapter_real_sql_collection_does_not_commit_failure(memory_db,mode):
    sessions,(uid,other)=memory_db;llm=service()
    llm._chat_completion=AsyncMock(return_value=completion(json.dumps({'preferences':[] if mode=='empty' else [{'category':'color','value':'blue','evidence':'I prefer blue'}]})))
    if mode=='failure':llm._chat_completion.side_effect=ConnectionError('private-failure')
    if mode=='cancel':llm._chat_completion.side_effect=asyncio.CancelledError()
    async with sessions() as db:
        memory=CustomerMemoryService(db)
        assert not await memory.collect(uid,'I prefer blue',llm)
        llm._chat_completion.assert_not_awaited()
        await memory.set_consent(uid,True)
        if mode in {'failure','cancel'}:
            with pytest.raises(asyncio.CancelledError if mode=='cancel' else Exception):
                await memory.collect(uid,'I prefer blue',llm)
        else:assert await memory.collect(uid,'I prefer blue',llm)==(mode=='candidate')
    async with sessions() as db:
        memory=CustomerMemoryService(db)
        assert await memory.recall(uid)==(['Customer explicitly prefers color: blue'] if mode=='candidate' else [])
        assert await memory.recall(other)==[]
