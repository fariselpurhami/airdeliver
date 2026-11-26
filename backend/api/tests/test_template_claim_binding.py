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

@pytest.mark.asyncio
async def test_grounded_customer_budget_remains_allowed_by_existing_numeric_validator():
 infer=AsyncMock(side_effect=[json.dumps({'text_template':'Your $80 budget is a limit, not proof of fit.'}),json.dumps(V)])
 text=await write_shopping_copy(infer,'budget $80',[catalog_result(row())],{'budget_max':'80'},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert '$80 budget' in text and infer.await_count==2

@pytest.mark.asyncio
async def test_literal_exact_catalog_name_binds_name_claim_without_rewriting_prose():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   refs=json.loads(messages[1]['content'])['claim_reference_map']
   price=next(k for k,v in refs.items() if v['field']=='price')
   return json.dumps({'text_template':card.name+' is listed at {{'+price+'}}.'})
  draft=json.loads(messages[1]['content'])['draft']
  assert {'product_id':card.id,'field':'name','value':card.name} in draft['claims']
  return json.dumps(V)
 assert await write_shopping_copy(infer,'x',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})==card.name+' is listed at '+card.price+'.'

@pytest.mark.asyncio
async def test_template_contract_avoids_literal_placeholder_duplication_and_reviews_decisive_unknown():
 calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:return json.dumps({'text_template':'Water resistance is not listed; no rain-safe choice is established.'})
  return json.dumps(V)
 await write_shopping_copy(infer,'rain safe',[catalog_result(row())],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert 'Do not type a literal product name beside its name placeholder' in calls[0][0]['content']
 assert 'A decisive unverified requirement prevents a proven suitability claim' in calls[1][0]['content']

@pytest.mark.asyncio
async def test_template_duplicate_full_name_parenthesis_fails_before_review():
 card=catalog_result(row());calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   refs=json.loads(messages[1]['content'])['claim_reference_map']
   name=next(k for k,v in refs.items() if v['field']=='name')
   return json.dumps({'text_template':card.name+' ({{'+name+'}}, listed candidate) is a conditional option.'})
  return json.dumps(V)
 with pytest.raises(ValueError,match='duplicate_product_name'):
  await write_shopping_copy(infer,'x',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert len(calls)==1

@pytest.mark.asyncio
async def test_exact_product_name_can_recur_in_distinct_sentences():
 card=catalog_result(row());infer=AsyncMock(side_effect=[json.dumps({'text_template':card.name+' is listed. Verify fit before considering '+card.name+'.'}),json.dumps(V)])
 text=await write_shopping_copy(infer,'x',[card],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'template_v1'})
 assert text.count(card.name)==2 and infer.await_count==2
