"""Actual writer boundary rejects numeric fragments despite positive review."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import write_shopping_copy,ShoppingCopyError

@pytest.mark.asyncio
@pytest.mark.parametrize('listed,prose',[('116','16'),('99','9'),('100.68','100'),('100.68','68'),('1,024','024')])
async def test_numeric_substring_cannot_borrow_larger_claim(listed,prose):
    card=catalog_result(SimpleNamespace(id=7,name='Atlas',sku='',is_active=True,inventory=3,price='20',currency='USD',category='electronics',attributes={'capacity':listed}))
    draft={'text':f'Atlas lists {prose} capacity.','product_ids':[7],'claims':[{'product_id':7,'field':'name','value':'Atlas'},{'product_id':7,'field':'spec.capacity','value':listed}]}
    infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])
    with pytest.raises(ShoppingCopyError):await write_shopping_copy(infer,'Atlas',[card],{},'catalog_results',2)
    infer.assert_awaited_once()

@pytest.mark.asyncio
@pytest.mark.parametrize('number',['116','100.68','1,024'])
async def test_whole_recorded_numeric_token_keeps_independent_review(number):
    card=catalog_result(SimpleNamespace(id=7,name='Atlas',sku='',is_active=True,inventory=3,price='20',currency='USD',category='electronics',attributes={'capacity':number}))
    draft={'text':f'Atlas lists {number} capacity.','product_ids':[7],'claims':[{'product_id':7,'field':'name','value':'Atlas'},{'product_id':7,'field':'spec.capacity','value':number}]}
    infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])
    result=await write_shopping_copy(infer,'Atlas',[card],{},'catalog_results',2)
    assert result==draft['text'] and infer.await_count==2
