"""Actual strict completion adapter rejects ambiguous JSON, not legacy API removal."""
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import StructuredOutputError
from tests.test_llm_execution_limits import service,completion

@pytest.mark.asyncio
@pytest.mark.parametrize('raw',[
 '{"category":"style","category":"color","value":"blue","evidence":"I prefer blue"}',
 '{"nested":{"x":1,"x":2}}','{"x":NaN}','{"x":Infinity}',
 '[]','null','{}'+(' '*32768),
])
async def test_actual_strict_json_adapter_rejects_ambiguous_nonobjects(raw):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(raw))
    # Whitespace normalization trims trailing spaces; use a real large value.
    if len(raw)>32768:llm._chat_completion.return_value=completion('{"x":"'+'x'*32768+'"}')
    with pytest.raises(StructuredOutputError):
        await llm.generate_response_strict(prompt='customer data',system_role='test',response_format='json_object')

@pytest.mark.asyncio
async def test_legacy_non_strict_adapter_keeps_original_shape_and_plain_text():
    llm=service();llm._chat_completion=AsyncMock(return_value=completion('[1,2]'))
    assert await llm.generate_response(prompt='data',system_role='test',response_format='json_object')=='[1,2]'
    llm._chat_completion.return_value=completion('A plain reply')
    assert await llm.generate_response_strict(prompt='data',system_role='test')=='A plain reply'

@pytest.mark.asyncio
async def test_preference_extractor_uses_same_strict_return_boundary():
    llm=service();llm._chat_completion=AsyncMock(return_value=completion('{"category":"style","category":"color","value":"blue","evidence":"I prefer blue"}'))
    with pytest.raises(StructuredOutputError):await llm.extract_shopping_preferences('I prefer blue')
