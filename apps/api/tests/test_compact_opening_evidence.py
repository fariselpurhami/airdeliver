"""Real offline prompt/schema sizes, unchanged cards and independent review."""
import json
from types import SimpleNamespace
import pytest
from app.services.opening_batch_copy import write_batch,opening_schema,RULES,REVIEW
from app.services.structured_output import response_format,strict_schema
from app.services.shared_provider_admission import estimated_tokens
from tests.test_shopping_discovery_contract import row
from tests.test_opening_batch_copy import body

@pytest.mark.asyncio
async def test_deduplicated_catalog_preserves_every_row_card_and_review_snapshot():
 groups=[(label,[row(id=i,name=f'Catalog Item {i}',attributes={'material':'cotton'}) for i in range(1,11)]) for label in ('Personalized','Bestsellers','Trending','Deals')]
 seen=[];draft=body(groups)
 async def infer(messages):
  seen.append(messages)
  return json.dumps(draft if len(seen)==1 else dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
 result=await write_batch(SimpleNamespace(infer_sales_json=infer),groups)
 assert len(result)==4 and len(seen)==2
 payload=json.loads(seen[0][1]['content'])
 assert len(payload['catalog'])==10 and all(r['card_ids']==list(range(1,11)) for r in payload['rows'])
 assert json.loads(seen[1][1]['content'])['input']==payload
 wire=response_format('openai/gpt-oss-120b',opening_schema(result))
 writer=estimated_tokens(seen[0],wire)+1800
 review=estimated_tokens(seen[1],response_format('openai/gpt-oss-120b',__import__('app.services.shopping_copy',fromlist=['GroundingReview']).GroundingReview))+256
 assert writer+review<7200
 # Old repeated-card evidence was materially larger for the same exact facts.
 old={'rows':[{'row':r['row'],'cards':payload['catalog']} for r in payload['rows']]}
 assert len(json.dumps(payload))<len(json.dumps(old))*.55


def test_annotation_compaction_never_removes_required_bounds_or_descriptions():
 schema=strict_schema(opening_schema(['Personalized','Deals']))
 assert schema['required']==['Personalized','Deals'] and schema['additionalProperties'] is False
 item=schema['$defs']['OpeningParagraphDraft']
 assert set(item['required'])=={'introduction','insight','product_ids','claims'}
 assert item['properties']['claims']['maxItems']==10
 assert item['properties']['introduction']['maxLength']==350
 assert 'title' not in json.dumps(schema)

@pytest.mark.asyncio
async def test_conflicting_same_id_evidence_fails_before_writer():
 calls=[]
 async def infer(messages):calls.append(messages);raise AssertionError('must not invoke')
 from app.services.shopping_copy import ShoppingCopyError
 with pytest.raises(ShoppingCopyError):
  await write_batch(SimpleNamespace(infer_sales_json=infer),[('Personalized',[row(id=1)]),('Deals',[row(id=1,name='Other')])])
 assert calls==[]

@pytest.mark.asyncio
@pytest.mark.parametrize('bad',['missing_required','array_too_long'])
async def test_opening_reported_schema_failures_never_publish_or_invoke_review(bad):
 from unittest.mock import AsyncMock
 from pydantic import ValidationError
 groups=[('Personalized',[row()])];draft=body(groups)
 if bad=='missing_required':draft['Personalized'].pop('insight')
 else:draft['Personalized']['claims']=[dict(product_id=1,field='name',value='Studio Headphones')]*11
 infer=AsyncMock(return_value=json.dumps(draft))
 from app.services.shopping_copy import ShoppingCopyError
 with pytest.raises(ShoppingCopyError) as caught:await write_batch(SimpleNamespace(infer_sales_json=infer),groups)
 assert caught.value.stage=='writer_schema' and infer.await_count==1
 assert 'Required shape' in infer.await_args.args[0][0]['content']
 assert 'never add a card list' in infer.await_args.args[0][0]['content']


def test_unclassified_error_shape_never_emits_provider_or_customer_text():
 from app.services.provider_json_diagnostics import provider_error_shape
 shape=provider_error_shape(SimpleNamespace(body={'error':{'code':'private-key','type':'private-type','message':'private-message','failed_generation':'private-output','private-param':'private'}}))
 assert shape==dict(body_type='dict',nested_error=True,has_code=True,has_type=True,has_generation=True)
 assert 'private' not in json.dumps(shape)
 assert provider_error_shape(SimpleNamespace(body='private'))==dict(body_type='str',nested_error=False)
 shape=provider_error_shape(SimpleNamespace(body={'type':'json_validate_failed'}))
 assert shape['type']=='json_validate_failed'
