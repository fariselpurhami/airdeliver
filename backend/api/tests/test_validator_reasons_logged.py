"""Validator rejection reasons survive into ShoppingCopyError.reason (scripted model, no provider call)."""
import asyncio
import json
import pytest
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingCopyError, write_shopping_copy

NAME={'product_id':1,'field':'name','value':'Studio Headphones'}

@pytest.mark.parametrize('text,reason',[
 ('Studio Headphones are the best choice for you.','unsupported_superiority_claim'),
 ('Studio Headphones come with free shipping.','unclaimed_fulfillment_or_policy_claim'),
 ('Studio Headphones are in stock right now.','unclaimed_stock_claim'),
 ('Studio Headphones are waterproof.','unclaimed_spec_claim'),
])
def test_specific_validator_reason_is_reported_not_generic_valueerror(text,reason):
    card=catalog_result(row())
    async def infer(messages):
        return json.dumps({'text':text,'product_ids':[1],'claims':[NAME]})
    with pytest.raises(ShoppingCopyError) as caught:
        asyncio.run(write_shopping_copy(infer,'headphones',[card],{},'catalog_results',20))
    assert caught.value.stage=='writer_evidence'
    assert caught.value.reason==reason
