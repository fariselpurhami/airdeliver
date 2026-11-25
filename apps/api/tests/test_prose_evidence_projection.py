"""Public cards and local validators retain full data; both model passes get facts."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_copy import write_shopping_copy
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row

@pytest.mark.asyncio
async def test_writer_reviewer_keep_all_claimable_facts_and_stock_qualifiers_without_transport():
 card=catalog_result(row(image='https://invalid.example/private-transport',sku='PRIVATE-SKU',attributes={'material':'cotton'}))
 original=card.model_dump(mode='json')
 draft=dict(text='Explore these catalog designs.',product_ids=[],claims=[])
 verdict=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
 infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(verdict)])
 await write_shopping_copy(infer,'headphones',[card],{},'catalog_results',1)
 writer=json.loads(infer.await_args_list[0].args[0][1]['content'])
 review=json.loads(infer.await_args_list[1].args[0][1]['content'])
 expected={k:v for k,v in original.items() if k not in {'image','sku','attributes'}}
 assert writer['catalog_evidence']==[expected] and review['input']==writer
 assert card.model_dump(mode='json')==original
 assert all(k in expected for k in ('id','name','price','currency','price_status','catalog_specs','relation','evidence_kind','stock_status','availability_note','category'))
 assert 'private-transport' not in json.dumps(writer) and 'PRIVATE-SKU' not in json.dumps(writer)
