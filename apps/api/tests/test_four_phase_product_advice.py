"""Same writer/reviewer calls, original logical phases with honest evidence."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.sales_response_service import SalesResponseService
from tests.test_sales_response_service import request

TEXT='Explore the listed choice for your current need.\n\nThe card contains current catalog details; unlisted specifications stay unknown.\n\nCompare those details with your requirements before deciding. Compatibility is unverified.\n\nCheck the missing details before choosing; no item is reserved.'
V=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)

@pytest.mark.asyncio
@pytest.mark.parametrize('task',['search','comparison','consultation','specifications','setup','negotiation','objection'])
async def test_substantive_advice_has_explicit_four_phase_writer_and_independent_review(task):
    infer=AsyncMock(side_effect=[json.dumps(dict(text=TEXT,product_ids=[],claims=[])),json.dumps(V)])
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(evidence={'shopping_task':task}))
    assert result.text==TEXT and len(result.text.split('\n\n'))==4
    assert infer.await_count==2
    writer,review=[call.args[0] for call in infer.await_args_list]
    assert 'exactly four nonempty sections' in writer[0]['content']
    assert 'four generic filler paragraphs fails' in review[0]['content']
    assert json.loads(writer[1]['content'])['request_evidence']['product_answer_shape']=='four_phase'
    assert json.loads(review[1]['content'])['input']['request_evidence']['product_answer_shape']=='four_phase'

@pytest.mark.asyncio
@pytest.mark.parametrize('mode,task,intent',[('catalog_results','price_inquiry','PRODUCT_SEARCH'),('clarification','search','GIFT_DISCOVERY'),('conversation','search','SOCIAL_CHAT'),('catalog_results','search','OPENING_INSIGHT')])
async def test_short_and_opening_exceptions_are_not_forced_into_four_phases(mode,task,intent):
    infer=AsyncMock(side_effect=[json.dumps(dict(text='What detail matters to you?',product_ids=[],claims=[])),json.dumps(V)])
    req=request(mode=mode,intent=intent,products=() if mode!='catalog_results' else request().products,evidence={'shopping_task':task,'sales_intent':intent})
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(req)
    assert result.text=='What detail matters to you?'
    assert 'exactly four nonempty sections' not in infer.await_args_list[0].args[0][0]['content']

@pytest.mark.asyncio
async def test_reviewer_can_withhold_bad_shape_without_repair_or_extra_calls():
    infer=AsyncMock(side_effect=[json.dumps(dict(text=TEXT,product_ids=[],claims=[])),json.dumps({**V,'fulfills_discovery_task':False})])
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request())
    assert result.response_kind=='system_notice' and result.products==[] and infer.await_count==2
