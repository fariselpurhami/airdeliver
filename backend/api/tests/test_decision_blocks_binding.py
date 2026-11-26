"""Model chooses paragraph/bullet composition, application serializes spacing only."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_copy import write_shopping_copy
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row
V=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
CTX={'product_answer_shape':'adaptive','claim_binding':'decision_blocks_v1'}

@pytest.mark.asyncio
@pytest.mark.parametrize('kinds',[['paragraph'],['paragraph','paragraph'],['paragraph','bullet','bullet']])
async def test_model_selected_blocks_preserve_text_and_review_full_composition(kinds):
 calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   refs=json.loads(messages[1]['content'])['claim_reference_map'];name=next(k for k,v in refs.items() if v['field']=='name')
   blocks=[{'kind':kind,'text_template':('Conditionally prefer {{'+name+'}}.' if i==0 else 'Verify rain protection before choosing.')} for i,kind in enumerate(kinds)]
   return json.dumps({'decision':'conditional','preferred_product_id':1,'decisive_unknown':'Rain protection.','blocks':blocks})
  payload=json.loads(messages[1]['content'])
  assert len(payload['draft']['text'].splitlines())>=len(kinds)
  assert payload['decision_record']['decision']=='conditional'
  return json.dumps(V)
 text=await write_shopping_copy(infer,'rain',[catalog_result(row())],{},'catalog_results',1,CTX)
 assert text.startswith('Conditionally prefer ') and len(calls)==2
 assert ('\n\n' in text)==(len(kinds)>1)
 assert ('- Verify' in text)==('bullet' in kinds)

@pytest.mark.asyncio
@pytest.mark.parametrize('blocks',[[],[{'kind':'heading','text_template':'Buy now'}],[{'kind':'paragraph','text_template':'Invented 999 claim.'}],[{'kind':'paragraph','text_template':'One\n\nHidden block.'}]])
async def test_block_bounds_shape_and_evidence_fail_before_review(blocks):
 infer=AsyncMock(return_value=json.dumps({'decision':'no_pick','preferred_product_id':None,'decisive_unknown':'Rain protection.','blocks':blocks}))
 with pytest.raises(ValueError):await write_shopping_copy(infer,'rain',[catalog_result(row())],{},'catalog_results',1,CTX)
 assert infer.await_count==1

@pytest.mark.asyncio
@pytest.mark.parametrize('review',[{**V,'supported':False},RuntimeError('synthetic outage')])
async def test_composed_blocks_never_bypass_independent_review(review):
 draft={'decision':'no_pick','preferred_product_id':None,'decisive_unknown':'Rain protection.','blocks':[{'kind':'paragraph','text_template':'Rain protection remains unknown.'}]}
 infer=AsyncMock(side_effect=[json.dumps(draft),review if isinstance(review,Exception) else json.dumps(review)])
 with pytest.raises(ValueError):await write_shopping_copy(infer,'rain',[catalog_result(row())],{},'catalog_results',1,CTX)
 assert infer.await_count==2

@pytest.mark.asyncio
async def test_blocks_cannot_invent_customer_laptop_dimension_even_with_grounded_budget():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages)
  data=json.loads(messages[1]['content']);refs=data['claim_reference_map']
  key=next(k for k,v in refs.items() if v['field']=='name')
  return json.dumps({'decision':'conditional','preferred_product_id':card.id,'decisive_unknown':'Rain protection.','blocks':[{'kind':'paragraph','text_template':'{{'+key+'}} fits your 15-inch laptop within your $80 budget.'}]})
 with pytest.raises(ValueError,match='unsupported_numeric_or_link_claim'):
  await write_shopping_copy(infer,'Rain with my laptop, budget $80',[card],{'budget':'$80','budget_max':'80','budget_currency':'USD'},'catalog_results',1,CTX)
 assert len(calls)==1

@pytest.mark.asyncio
async def test_blocks_known_numeric_spec_is_not_proof_of_customer_fit():
 from types import SimpleNamespace
 item=row();item.attributes={'laptop_fit':'up to 15-inch laptop'}
 card=catalog_result(item);calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   refs=json.loads(messages[1]['content'])['claim_reference_map'];name=next(k for k,v in refs.items() if v['field']=='name');fit=next(k for k,v in refs.items() if v['field']=='spec.laptop_fit')
   return json.dumps({'decision':'conditional','preferred_product_id':card.id,'decisive_unknown':'Rain protection.','blocks':[{'kind':'paragraph','text_template':'{{'+name+'}} fits your laptop because it lists {{'+fit+'}}.'}]})
  data=json.loads(messages[1]['content'])
  assert 'fits your laptop' in data['draft']['text']
  assert data['input']['customer_message']=='Rain with my laptop'
  return json.dumps({**V,'supported':False})
 with pytest.raises(ValueError,match='grounding_review_rejected'):
  await write_shopping_copy(infer,'Rain with my laptop',[card],{},'catalog_results',1,CTX)
 assert len(calls)==2
