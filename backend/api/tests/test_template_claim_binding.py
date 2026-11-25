"""Model-authored prose with exact evidence placeholders, offline opt-in preparation."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_copy import write_shopping_copy
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row
V=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)


@pytest.mark.asyncio
async def test_template_refs_compile_exact_values_and_claims_before_unchanged_review():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   refs=json.loads(messages[1]['content'])['claim_reference_map']
   keys={v['field']:k for k,v in refs.items()}
   return json.dumps({'text_template':'Prefer {{'+keys['name']+'}} at {{'+keys['price']+'}} {{'+keys['currency']+'}}; fit remains unverified.'})
  draft=json.loads(messages[1]['content'])['draft']
  assert draft['text']==f'Prefer {card.name} at {card.price} {card.currency}; fit remains unverified.'
  assert {c['field'] for c in draft['claims']}=={'name','price','currency'}
  assert draft['product_ids']==[card.id]
  return json.dumps(V)
 text=await write_shopping_copy(infer,'prefer one',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert card.price in text and len(calls)==2


@pytest.mark.asyncio
@pytest.mark.parametrize('text',['Unknown {{c999}}','A made-up 25 difference.','Internal ID 1.','Broken {{c0}', 'Bare {c0}'])
async def test_template_unknown_refs_free_numbers_and_malformed_placeholders_fail_closed(text):
 infer=AsyncMock(return_value=json.dumps({'text_template':text}))
 with pytest.raises(ValueError):
  await write_shopping_copy(infer,'x',[catalog_result(row())],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert infer.await_count==1


@pytest.mark.asyncio
async def test_compiled_template_still_requires_independent_positive_review():
 infer=AsyncMock(side_effect=[json.dumps({'text_template':'The required evidence is not listed.'}),json.dumps({**V,'supported':False})])
 with pytest.raises(ValueError,match='grounding_review_rejected'):
  await write_shopping_copy(infer,'x',[catalog_result(row())],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert infer.await_count==2
