import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from groq import BadRequestError
from app.services.neural_core_service import NeuralCoreService, NeuralCoreConfig, SessionMemory


@pytest.mark.asyncio
async def test_permanent_provider_rejection_is_not_retried():
    service = NeuralCoreService(object(), object())
    response = httpx.Response(400, request=httpx.Request('POST', 'https://example.invalid'))
    create = AsyncMock(side_effect=BadRequestError('invalid request',response=response,body={}))
    service.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(BadRequestError):
        await service._execute_llm_inference([])
    assert create.await_count == 1


@pytest.mark.asyncio
async def test_entire_router_attempt_obeys_total_deadline(monkeypatch):
    service = NeuralCoreService(object(), object()); service.is_healthy=True
    cancelled=asyncio.Event()
    async def slow(messages):
        try:
            await asyncio.sleep(0.12)
            return json.dumps({'intent':'PRODUCT_SEARCH','query':'too late'})
        finally:
            cancelled.set()
    monkeypatch.setattr(service,'_execute_llm_inference',slow)
    monkeypatch.setattr(NeuralCoreConfig,'LLM_TIMEOUT_SEC',0.01)
    result=await service._analyze_intent('headphones',SessionMemory(user_name='Client'))
    assert result.intent=='SOCIAL_CHAT'
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_malformed_provider_output_not_logged(caplog):
    service=NeuralCoreService(object(),object());service.is_healthy=True
    async def invalid(messages):return json.dumps({'intent':'private-provider-content'})
    service._execute_llm_inference=invalid
    await service._analyze_intent('message',SessionMemory(user_name='Client'))
    assert 'private-provider-content' not in caplog.text
    assert all(not hasattr(record,'raw_payload') for record in caplog.records)
