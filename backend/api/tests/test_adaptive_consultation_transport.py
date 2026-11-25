"""Actual consultation/transport adapter with controlled completions, no providers."""
import json
from unittest.mock import AsyncMock
import pytest
from tests.test_llm_execution_limits import service,completion
from tests.test_sales_response_service import request


@pytest.mark.asyncio
@pytest.mark.parametrize('reject',[False,True])
async def test_consultation_opt_in_references_preserve_independent_review_and_budgets(reject):
 svc=service();calls=[];card=request().products[0]
 async def respond(**kwargs):
  calls.append(kwargs)
  name=kwargs['response_format']['json_schema']['name']
  if name=='ReferencedShoppingDraft':
   data=json.loads(kwargs['messages'][1]['content'])
   refs=[key for key,value in data['claim_reference_map'].items() if value['field']=='name']
   return completion(json.dumps({'text':card.name+' is listed; the requested material is not specified.','product_ids':[card.id],'claim_refs':refs}))
  assert name=='GroundingReview'
  draft=json.loads(kwargs['messages'][1]['content'])['draft']
  assert draft['claims']==[{'product_id':card.id,'field':'name','value':card.name}]
  return completion(json.dumps({'supported':not reject,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True}))
 svc._chat_completion=AsyncMock(side_effect=respond)
 result=await svc.consult_catalog(question='What material is listed?',cards=[card],evidence={'claim_binding':'references_v1'})
 assert len(calls)==2
 assert [call['max_tokens'] for call in calls]==[1200,256]
 assert calls[1].get('reasoning_effort')=='low'
 assert result.response_kind==('system_notice' if reject else 'catalog_results')
 assert result.products==([] if reject else [card])


@pytest.mark.asyncio
async def test_consultation_default_does_not_silently_enable_experimental_wire_format():
 svc=service();names=[]
 async def respond(**kwargs):
  name=kwargs['response_format']['json_schema']['name'];names.append(name)
  return completion(json.dumps({'text':'The requested material is not specified.','product_ids':[],'claims':[]} if name=='ShoppingDraft' else {'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True}))
 svc._chat_completion=AsyncMock(side_effect=respond)
 result=await svc.consult_catalog(question='What material is listed?',cards=list(request().products))
 assert result.response_kind=='catalog_results'
 assert names==['ShoppingDraft','GroundingReview']
