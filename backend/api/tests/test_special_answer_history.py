# Historical retained-method contracts. New production bridge is tested separately.
"""History plumbing through specialized response branches, no provider calls."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory,RequestContext,SearchPlan,SearchConstraints


@pytest.mark.asyncio
@pytest.mark.parametrize('branch',['informational','specs','recovery'])
async def test_specialized_answer_receives_history_as_user_data_not_policy(branch):
    llm=SimpleNamespace(generate_response=AsyncMock(return_value='Grounded answer'))
    service=AINLUService(object(),object(),object(),object(),llm)
    service._get_conversation_context=AsyncMock(return_value='HISTORY_MARKER: previously discussed Atlas Headphones. Customer explicitly prefers color: blue')
    service._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona='explorer',tier='MEDIUM'))
    service._safe_web_search=AsyncMock(return_value='Official catalog evidence' if branch=='informational' else '')
    service._enrich_specs_context=AsyncMock(return_value='Battery: not verified')
    service._perform_smart_recovery=AsyncMock(return_value=[])
    category=IntentCategory.COMPARISON if branch=='informational' else IntentCategory.PRICE_INQUIRY
    intent=CommerceIntentPayload(category=category,is_chitchat=False)
    request=service._parse_incoming_message({'user_id':17,'message':'What about that item?'})
    plan=SearchPlan('headphones','',SearchConstraints(clean_query='headphones'),branch=='specs',False)
    products=[] if branch=='recovery' else [{'id':7,'name':'Atlas Headphones','description':'Listed catalog details','price':'49.00','inventory':3}]
    answer=await service._synthesize_response_legacy_unreviewed(request=request,ctx=RequestContext(17,'local',0),plan=plan,final_products=products,ai_response_prefix='',intent_payload=intent)
    assert answer.response_text=='Grounded answer'
    call=llm.generate_response.call_args.kwargs
    data=json.loads(call['prompt'])
    assert 'HISTORY_MARKER' in data['conversation_context']
    assert 'HISTORY_MARKER' not in call['system_role']
    assert 'current customer question wins' in call['system_role']
