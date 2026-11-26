"""Code, not the model, computes combined listed prices and remaining budget; the validator allows exactly those values.

Observed on a real Groq draft (n=1): "Oak Desk, Desk Lamp and Ceramic Mug together within 300" produced the
correct 287.00 and 13.00, and the whole answer was withheld because sums were not evidence-backed numbers.
"""
import json
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft, write_shopping_copy, exact_totals


def cards(**over):
    return [catalog_result(row(id=7,name='Oak Desk',price=Decimal('240.00'),category='furniture')),
            catalog_result(row(id=4,name='Desk Lamp',price=Decimal('35.00'),category='lighting')),
            catalog_result(row(id=8,name='Ceramic Mug',price=Decimal('12.00'),category='kitchen',**over))]

def draft(text):
    return ShoppingDraft(text=text,product_ids=[7,4,8],claims=[{'product_id':i,'field':'name','value':n} for i,n in ((7,'Oak Desk'),(4,'Desk Lamp'),(8,'Ceramic Mug'))])

BRIEF={'budget_max':'300'}


def test_totals_are_exact_decimals_from_card_prices():
    assert exact_totals(cards(),BRIEF)=={'combined_listed_price':'287.00','currency':'USD','budget_remaining':'13.00'}
    assert exact_totals(cards(),{})=={'combined_listed_price':'287.00','currency':'USD'}
    assert exact_totals(cards(),{'budget_max':'250'})=={'combined_listed_price':'287.00','currency':'USD','over_budget_by':'37.00'}


@pytest.mark.parametrize('c,brief',[
 (cards()[:1],BRIEF),                      # a single card has no combined total
 (cards(currency='EUR'),BRIEF),            # mixed currencies are never added
 ([cards()[0],catalog_result(row(id=9,name='Mystery',price=None))],BRIEF),   # unknown price is never guessed
])
def test_no_total_when_it_would_be_a_guess(c,brief):
    assert exact_totals(c,brief) is None


def test_the_exact_sum_and_remaining_are_accepted_without_claims():
    validate_draft(draft('Together the Oak Desk, Desk Lamp and Ceramic Mug come to 287.00 USD, leaving 13.00 USD.'),cards(),None,BRIEF)


@pytest.mark.parametrize('text',[
 'Together the Oak Desk, Desk Lamp and Ceramic Mug come to 290.00 USD.',
 'Together the Oak Desk, Desk Lamp and Ceramic Mug come to 287.00 USD, leaving 15.00 USD.',
 'The Oak Desk, Desk Lamp and Ceramic Mug come to 287.00 USD, a 20% saving.',
])
def test_any_other_number_stays_rejected(text):
    with pytest.raises(ValueError,match='unsupported_numeric_or_link_claim'):
        validate_draft(draft(text),cards(),None,BRIEF)


@pytest.mark.asyncio
async def test_writer_payload_carries_the_exact_totals_only_when_computable():
    seen=[]
    review=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
    async def infer(messages):
        seen.append(messages)
        return json.dumps(dict(text='Compare the listed design.',product_ids=[],claims=[]) if len(seen)%2 else review)
    await write_shopping_copy(infer,'total?',cards(),BRIEF,'catalog_results',1,{})
    await write_shopping_copy(infer,'one',cards()[:1],BRIEF,'catalog_results',1,{})
    assert json.loads(seen[0][1]['content'])['exact_totals']['combined_listed_price']=='287.00'
    assert 'exact_totals' not in json.loads(seen[2][1]['content'])
