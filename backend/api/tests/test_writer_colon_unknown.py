"""An honest 'Waterproof rating: unknown' was withheld because the colon split the term from its negation.

Observed on a real Groq draft (n=1, bait-01, low-1200): the draft said weight 650 g and listed volume and
waterproofing as unknown, and the validator rejected it as unclaimed_spec_claim.
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
    'The Trail Backpack is listed. Waterproof rating: unknown, the catalog does not list one.',
    'The Trail Backpack is listed. Waterproof rating: unknown.',
    'The Trail Backpack is listed. Waterproof rating: not listed.',
    'The Trail Backpack is listed. Waterproof: unverified.',
])
def test_colon_introduced_unknown_is_honest(text):
    validate_draft(draft(text),card())

@pytest.mark.parametrize('text',[
    'The Trail Backpack is waterproof.',
    'The Trail Backpack: waterproof and light.',
    'Waterproof rating: excellent, unknown brand though.',
    'The Trail Backpack has a waterproof rating: 5 stars.',
])
def test_affirmative_claims_still_rejected(text):
    with pytest.raises(ValueError):
        validate_draft(draft(text),card())
