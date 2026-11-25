# Historical retained-method contracts. New production bridge is tested separately.
"""Catalog presence is not a stock/dispatch claim."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory,RequestContext,SearchPlan,SearchConstraints


def service():return AINLUService(object(),object(),object(),object(),SimpleNamespace())


@pytest.mark.parametrize('fields,state',[
    ({},'not_verified'),({'inventory':3},'not_verified'),({'inventory':3,'is_active':True},'available_in_catalog'),
    ({'inventory':0,'is_active':True},'unavailable'),({'inventory':5,'is_active':False},'unavailable'),
    ({'inventory':True,'is_active':True},'not_verified'),({'inventory':-1,'is_active':True},'not_verified'),
])
def test_availability_needs_explicit_live_activity_and_stock(fields,state):
    assert service()._catalog_availability(dict({'id':7,'name':'headphones'},**fields))['availability']==state


@pytest.mark.asyncio
async def test_specs_answer_has_exact_price_and_stock_metadata_not_forced_instock():
    svc=service();svc.llm_service.generate_response=AsyncMock(return_value='Listed facts')
    svc._get_conversation_context=AsyncMock(return_value='')
    svc._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona='explorer',tier='MEDIUM'))
    svc._enrich_specs_context=AsyncMock(return_value='No battery specification')
    request=svc._parse_incoming_message({'user_id':17,'message':'What battery does it have?'})
    product={'id':7,'name':'headphones','price':'49.00','is_active':True,'inventory':0}
    await svc._synthesize_response_legacy_unreviewed(request=request,ctx=RequestContext(17,'local',0),plan=SearchPlan('headphones','',SearchConstraints(clean_query='headphones'),True,False),final_products=[product],ai_response_prefix='',intent_payload=CommerceIntentPayload(category=IntentCategory.PRICE_INQUIRY,is_chitchat=False))
    prompt=json.loads(svc.llm_service.generate_response.call_args.kwargs['prompt'])
    assert prompt['catalog_availability'][0]['availability']=='unavailable'
    assert prompt['catalog_availability'][0]['price']=='49.00'
    assert 'confirm the IN-STOCK' not in prompt['inquiry']
