"""Exact evidence references are resolved, never used to invent prose facts."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_copy import write_shopping_copy
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row

@pytest.mark.asyncio
async def test_adaptive_writer_uses_closed_claim_refs_and_reviewer_gets_exact_claims():
 card=catalog_result(row(attributes={'material':'canvas'}));calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   data=json.loads(messages[1]['content']);choices=data['claim_reference_map']
   refs=[key for key,val in choices.items() if val['field'] in {'name','spec.material'}]
   return json.dumps({'text':card.name+' lists canvas.','product_ids':[card.id],'claim_refs':refs})
  return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
 result=await write_shopping_copy(infer,'material',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'references_v1'})
 assert result==card.name+' lists canvas.' and len(calls)==2
 draft=json.loads(calls[1][1]['content'])['draft']
 assert {'product_id':card.id,'field':'spec.material','value':'canvas'} in draft['claims']
 assert 'claim_refs' not in draft

@pytest.mark.asyncio
async def test_unknown_claim_ref_is_not_repaired_or_reviewed():
 card=catalog_result(row());infer=AsyncMock(return_value=json.dumps({'text':card.name,'product_ids':[card.id],'claim_refs':['made-up']}))
 with pytest.raises(ValueError):await write_shopping_copy(infer,'x',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'references_v1'})
 assert infer.await_count==1

@pytest.mark.parametrize('refs',[['c0','c0'],['c999']])
def test_reference_resolver_rejects_duplicate_and_unknown_refs(refs):
 from app.services.shopping_copy import resolve_claim_references
 with pytest.raises(ValueError):
  resolve_claim_references(json.dumps({'text':'x','product_ids':[],'claim_refs':refs}),{'c0':{'product_id':1,'field':'name','value':'x'}})

@pytest.mark.asyncio
async def test_reference_binding_does_not_bypass_numeric_evidence_validation():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages);data=json.loads(messages[1]['content'])
  refs=[k for k,v in data['claim_reference_map'].items() if v['field']=='name']
  return json.dumps({'text':card.name+' costs 9999.','product_ids':[card.id],'claim_refs':refs})
 with pytest.raises(ValueError,match='unsupported_numeric_or_link_claim'):
  await write_shopping_copy(infer,'price',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'references_v1'})
 assert len(calls)==1

@pytest.mark.asyncio
async def test_reference_binding_keeps_independent_negative_review():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   data=json.loads(messages[1]['content'])
   refs=[k for k,v in data['claim_reference_map'].items() if v['field']=='name']
   return json.dumps({'text':card.name,'product_ids':[card.id],'claim_refs':refs})
  return json.dumps(dict(supported=False,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
 with pytest.raises(ValueError,match='grounding_review_rejected'):
  await write_shopping_copy(infer,'x',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'references_v1'})
 assert len(calls)==2

@pytest.mark.asyncio
async def test_reference_wire_contract_has_no_contradictory_object_output_instruction():
 card=catalog_result(row());seen=[]
 async def infer(messages):
  seen.append(messages)
  if len(seen)==1:return json.dumps({'text':'The requested detail is not listed.','product_ids':[],'claim_refs':[]})
  return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
 await write_shopping_copy(infer,'x',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'references_v1'})
 writer=seen[0][0]['content']
 assert 'Return JSON{text,product_ids,claims}' not in writer
 assert 'Copy needed claim objects' not in writer
 assert 'Do not calculate differences' in writer
 assert 'claim_reference_map' in writer
