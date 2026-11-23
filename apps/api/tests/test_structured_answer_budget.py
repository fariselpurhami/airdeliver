import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import FreeLLMService,_sanitize_structured_prompt


def test_large_catalog_cannot_slice_off_json_history_or_availability():
    prompt=json.dumps({'user_query':'What about its price?','product':{'description':'long catalog '*3000},'conversation_history':'HISTORY_MARKER same product','catalog_availability':{'availability':'not_verified'}})
    result=_sanitize_structured_prompt(prompt,14000)
    assert len(result)<=14000
    data=json.loads(result)
    assert data['conversation_history']=='HISTORY_MARKER same product'
    assert data['catalog_availability']['availability']=='not_verified'


@pytest.mark.asyncio
async def test_actual_wrapper_retains_late_context_as_valid_user_json():
    svc=FreeLLMService()
    svc._chat_completion=AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Catalog answer'))]))
    prompt=json.dumps({'inquiry':'catalog '*1600,'conversation_context':'LATE_HISTORY_MARKER','catalog_availability':[{'availability':'unavailable'}]})
    await svc.generate_response(prompt,system_role='Static policy')
    messages=svc._chat_completion.call_args.kwargs['messages']
    data=json.loads(messages[1]['content'])
    assert data['conversation_context']=='LATE_HISTORY_MARKER'
    assert data['catalog_availability'][0]['availability']=='unavailable'
    assert len(messages[1]['content'])<=14000
    assert 'LATE_HISTORY_MARKER' not in messages[0]['content']
