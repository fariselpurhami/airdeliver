"""The shopping writer shares the 1200-token cap with reasoning, so it runs gpt-oss at low reasoning effort.

Observed once on real Groq (n=1): 1010 of 1200 completion tokens were reasoning, finish_reason=length,
and an otherwise valid draft was withheld as "Sales completion exceeded output budget".
"""
import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock


async def call(model,schema):
    from app.services.free_llm_service import FreeLLMService
    from app.services.shopping_copy import ShoppingDraft, GroundingReview
    svc=object.__new__(FreeLLMService);svc.__init__();svc.models=SimpleNamespace(brain_model=model)
    calls=[]
    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'),finish_reason='stop')])
    svc._get_client=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    await svc.infer_sales_json([{'role':'user','content':'x'}],response_schema={'draft':ShoppingDraft,'review':GroundingReview}[schema])
    return calls[0]


@pytest.mark.asyncio
async def test_writer_draft_runs_at_low_reasoning_effort_on_gpt_oss():
    sent=await call('openai/gpt-oss-120b','draft')
    assert sent['reasoning_effort']=='low' and sent['max_tokens']==1200


@pytest.mark.asyncio
async def test_other_models_get_no_reasoning_parameter():
    assert 'reasoning_effort' not in await call('llama-3.3-70b-versatile','draft')
