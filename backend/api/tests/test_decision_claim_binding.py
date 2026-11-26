"""Opt-in model-authored decision record is reviewed in the same two-call flow."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_copy import write_shopping_copy
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row
V=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)

@pytest.mark.asyncio
async def test_decision_record_and_compiled_prose_both_reach_independent_review():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   refs=json.loads(messages[1]['content'])['claim_reference_map'];name=next(k for k,v in refs.items() if v['field']=='name')
   return json.dumps({'decision':'conditional','preferred_product_id':card.id,'decisive_unknown':'Water resistance is not listed.','text_template':'Conditionally prefer {{'+name+'}} only after confirming water resistance.'})
  reviewed=json.loads(messages[1]['content'])
  assert reviewed['decision_record']=={'decision':'conditional','preferred_product_id':card.id,'decisive_unknown':'Water resistance is not listed.'}
  assert reviewed['draft']['product_ids']==[card.id]
  return json.dumps(V)
 assert 'Conditionally prefer' in await write_shopping_copy(infer,'rain',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'decision_v1'})
 assert len(calls)==2

@pytest.mark.asyncio
@pytest.mark.parametrize('patch',[{'decision':'pick','decisive_unknown':'Missing rain evidence.'},{'decision':'conditional','decisive_unknown':''},{'decision':'no_pick','preferred_product_id':1},{'preferred_product_id':999}])
async def test_inconsistent_decision_record_fails_before_review(patch):
 data={'decision':'conditional','preferred_product_id':1,'decisive_unknown':'Missing rain evidence.','text_template':'Check missing rain evidence.'};data.update(patch)
 infer=AsyncMock(return_value=json.dumps(data))
 with pytest.raises(ValueError):await write_shopping_copy(infer,'rain',[catalog_result(row())],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'decision_v1'})
 assert infer.await_count==1

@pytest.mark.asyncio
async def test_reviewed_no_pick_has_no_preferred_identity():
 calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:return json.dumps({'decision':'no_pick','preferred_product_id':None,'decisive_unknown':'Neither lists water resistance.','text_template':'Neither listing establishes rain protection. Verify that before choosing.'})
  assert json.loads(messages[1]['content'])['decision_record']['preferred_product_id'] is None
  return json.dumps(V)
 assert 'rain protection' in await write_shopping_copy(infer,'rain',[catalog_result(row())],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'decision_v1'})
