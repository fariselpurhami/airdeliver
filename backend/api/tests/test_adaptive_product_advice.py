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
