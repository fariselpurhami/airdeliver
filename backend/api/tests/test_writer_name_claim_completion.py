"""A product named in the text and listed in product_ids gets its name claim from the card itself.

The name claim carries no model knowledge (it is the exact card name), so a draft that only forgot to
list it is completed deterministically instead of being withheld. Nothing else about validation changes.
"""
import json
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingCopyError, ShoppingDraft, validate_draft, write_shopping_copy


def card(): return catalog_result(row(id=9,name='Wool Scarf',price=Decimal('30.00'),category='accessories'))
PRICE={'product_id':9,'field':'price','value':'30.00'}
REVIEW=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)


async def run(draft):
    seen=[]
    async def infer(messages):
        seen.append(messages)
        return json.dumps(draft if len(seen)==1 else REVIEW)
    return await write_shopping_copy(infer,'is the scarf available',[card()],{},'catalog_results',1,{})


@pytest.mark.asyncio
async def test_name_claim_the_model_forgot_is_completed_from_the_card():
    out=await run(dict(text="I can't confirm merchant stock for the Wool Scarf, listed at 30.00 USD.",product_ids=[9],claims=[PRICE]))
    assert 'Wool Scarf' in out


@pytest.mark.asyncio
async def test_name_not_in_the_text_is_not_invented_as_a_mention():
    # product_ids lists the product but the text never names it: stays rejected, not silently completed.
    with pytest.raises(ShoppingCopyError,match='undeclared_product_mention'):
        await run(dict(text='The listed price is 30.00 USD.',product_ids=[9],claims=[PRICE]))


def test_validator_itself_is_unchanged():
    with pytest.raises(ValueError,match='undeclared_product_mention'):
        validate_draft(ShoppingDraft(text='Wool Scarf is listed.',product_ids=[9],claims=[PRICE]),[card()],None,{})
