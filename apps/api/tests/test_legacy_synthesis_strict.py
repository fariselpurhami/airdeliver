"""Legacy specialized response failures must not turn into product claims."""
import asyncio,logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory,RequestContext,SearchPlan,SearchConstraints
from tests.test_llm_execution_limits import service,completion

@pytest.mark.asyncio
@pytest.mark.parametrize('branch',['informational','specs','recovery'])
@pytest.mark.parametrize('failure',['transport','blank','cancel','success'])
async def test_specialized_strict_boundaries(branch,failure,caplog):
    llm=service();svc=AINLUService(object(),object(),object(),object(),llm)
    svc._get_conversation_context=AsyncMock(return_value='Earlier customer reference')
    svc._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona='explorer',tier='MEDIUM'))
    svc._safe_web_search=AsyncMock(return_value='Bounded source evidence' if branch=='informational' else '')
    svc._enrich_specs_context=AsyncMock(return_value='Battery: unverified')
    svc._perform_smart_recovery=AsyncMock(return_value=[])
    if failure=='transport':llm._chat_completion=AsyncMock(side_effect=ConnectionError('private failure sentinel'))
    elif failure=='cancel':llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    else:llm._chat_completion=AsyncMock(return_value=completion('Grounded answer' if failure=='success' else ''))
    category=IntentCategory.COMPARISON if branch=='informational' else IntentCategory.PRICE_INQUIRY
    intent=CommerceIntentPayload(category=category,is_chitchat=False)
    request=svc._parse_incoming_message({'user_id':17,'message':'private customer sentinel'})
    plan=SearchPlan('chair','',SearchConstraints(clean_query='chair'),branch=='specs',False)
    products=[] if branch=='recovery' else [{'id':7,'name':'Listed chair','description':'catalog details','price':'49.00','inventory':3}]
    kwargs=dict(request=request,ctx=RequestContext(17,'local',0),plan=plan,final_products=products,ai_response_prefix='',intent_payload=intent)
    if failure=='cancel':
        with pytest.raises(asyncio.CancelledError):await svc._synthesize_response(**kwargs)
        return
    with caplog.at_level(logging.ERROR):answer=await svc._synthesize_response(**kwargs)
    if failure=='success':assert answer.response_text=='Grounded answer'
    else:
        assert 'could not verify' in answer.response_text
        for claim in ['matches the specs','best alternative','live inventory global warehouses','synchronizing']:
            assert claim not in answer.response_text
        assert 'private failure sentinel' not in caplog.text
        assert 'private customer sentinel' not in caplog.text
    assert [p['id'] for p in answer.products]==[p['id'] for p in products]
