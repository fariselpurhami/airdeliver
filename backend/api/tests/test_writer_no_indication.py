"""Honest 'no indication that it is waterproof' and curly-apostrophe negations were withheld.

Observed on a real Groq draft (n=1, bait-01, def-2400): "there's no indication that it's waterproof" and
"we can't confirm ..." (curly apostrophe) read as unclaimed spec claims.
"""
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft


def card():
    return [catalog_result(row(id=2,name='Trail Backpack',price=Decimal('59.00'),category='bags'))]

def draft(text):
    return ShoppingDraft(text=text,product_ids=[2],claims=[{'product_id':2,'field':'name','value':'Trail Backpack'}])

@pytest.mark.parametrize('text',[
    'The Trail Backpack is listed. There is no indication that it is waterproof.',
    'The Trail Backpack is listed, and there\u2019s no indication that it\u2019s waterproof.',
    'The Trail Backpack is listed. We can\u2019t confirm that it is waterproof.',
    'The Trail Backpack is listed. The catalog has no mention of waterproofing.',
    'The Trail Backpack is listed. There is no evidence it is waterproof.',
])
def test_honest_absence_wording_passes(text):
    validate_draft(draft(text),card())

@pytest.mark.parametrize('text',[
    'The Trail Backpack is waterproof.',
    'There is no doubt that the Trail Backpack is waterproof.',
    'No problem, the Trail Backpack is waterproof.',
    'There is no indication of wear, and it is waterproof.',
])
def test_affirmative_claims_still_rejected(text):
    with pytest.raises(ValueError):
        validate_draft(draft(text),card())
