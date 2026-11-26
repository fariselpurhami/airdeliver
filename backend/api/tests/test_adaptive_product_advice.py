"""Latest owner standard: answer shape follows the question, not four slots."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.sales_response_service import SalesResponseService
from tests.test_sales_response_service import request
V=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)

@pytest.mark.asyncio
@pytest.mark.parametrize('task,text',[
 ('search','**Start with the listed option.**\n\n- Check the missing fit detail before choosing.'),
 ('comparison','**Decision:** neither has enough compatibility evidence.\n\nCompare the listed facts; confirm the required connection first.'),
 ('consultation','A useful choice depends on the missing compatibility detail.'),
 ('specifications','The requested specification is not listed.'),
 ('negotiation','No discount is listed; the shown price is the only evidenced amount.'),
])
async def test_active_service_uses_adaptive_writer_and_independent_review(task,text):
 infer=AsyncMock(side_effect=[json.dumps(dict(text=text,product_ids=[],claims=[])),json.dumps(V)])
 result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(evidence={'shopping_task':task}))
 assert result.text==text and infer.await_count==2
 writer,review=[c.args[0] for c in infer.await_args_list]
 assert json.loads(writer[1]['content'])['request_evidence']['product_answer_shape']=='adaptive'
 for messages in (writer,review):
  assert 'Do not force four sections' in messages[0]['content']
  assert 'exactly four nonempty sections' not in messages[0]['content']
 assert 'Reject repetitive filler' in review[0]['content']

@pytest.mark.asyncio
async def test_adaptive_shape_does_not_bypass_review_failure():
 infer=AsyncMock(side_effect=[json.dumps(dict(text='A concise answer.',product_ids=[],claims=[])),json.dumps({**V,'fulfills_discovery_task':False})])
 result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request())
 assert result.response_kind=='system_notice' and result.products==[] and infer.await_count==2

@pytest.mark.asyncio
async def test_material_does_not_prove_weather_performance_and_prose_has_no_ids():
 infer=AsyncMock(side_effect=[json.dumps(dict(text='Water resistance is not listed; check it before choosing.',product_ids=[],claims=[])),json.dumps(V)])
 await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request())
 for call in infer.await_args_list:
  rules=call.args[0][0]['content']
  assert 'Material alone does not prove water resistance' in rules
  assert 'Do not print internal product IDs' in rules
  assert 'exact full product name' in rules

@pytest.mark.asyncio
async def test_claim_choices_are_exact_card_values_not_generated_facts():
 infer=AsyncMock(side_effect=[json.dumps(dict(text='Check the listed material.',product_ids=[],claims=[])),json.dumps(V)])
 req=request();await SalesResponseService(infer,provider_ready=True,timeout=1).respond(req)
 payload=json.loads(infer.await_args_list[0].args[0][1]['content'])
 options=payload['catalog_evidence'][0]['claim_options']
 assert {'product_id':req.products[0].id,'field':'name','value':req.products[0].name} in options
 assert all(c['field'] in {'name','price','currency','evidence_kind','stock_status'} or c['field'].startswith('spec.') for c in options)
 assert 'Copy needed claim objects' in infer.await_args_list[0].args[0][0]['content']
