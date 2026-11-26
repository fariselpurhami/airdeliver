"""Terms the customer asked about and the catalog lacks may be answered with any honest absence wording.

Observed on real Groq drafts (n=1 each, bait-01, low-1200 and def-2400): three different honest phrasings of
"waterproofing is unknown" were rejected in a row. Judged per sentence and only for terms in the customer's message.
"""
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft

ASK='Is the Trail Backpack waterproof, and how many liters?'

def card():
    return [catalog_result(row(id=2,name='Trail Backpack',price=Decimal('59.00'),category='bags'))]

def draft(text):
    return ShoppingDraft(text=text,product_ids=[2],claims=[{'product_id':2,'field':'name','value':'Trail Backpack'}])

@pytest.mark.parametrize('text',[
    'The Trail Backpack is listed. Waterproof rating: unknown \u2013 no waterproof claim is provided.',
    'The Trail Backpack is listed. The catalog gives nothing on waterproofing, so I can\u2019t say either way.',
    'The Trail Backpack is listed. I would not call it waterproof, since the catalog is silent on that.',
    'The Trail Backpack is listed. Nothing here shows it is waterproof.',
])
def test_asked_absent_term_with_any_absence_wording_passes(text):
    validate_draft(draft(text),card(),None,None,ASK)

@pytest.mark.parametrize('text',[
    'The Trail Backpack is waterproof.',
    'No problem, the Trail Backpack is waterproof.',
    'Yes, it is waterproof, no worries about rain.',
    'The Trail Backpack is waterproof. Capacity is not listed.',
    'Capacity is unknown, but the Trail Backpack is waterproof.',
])
def test_affirmative_claims_still_rejected_even_when_asked(text):
    with pytest.raises(ValueError):
        validate_draft(draft(text),card(),None,None,ASK)

def test_term_the_customer_did_not_raise_stays_strict():
    with pytest.raises(ValueError):
        validate_draft(draft('The Trail Backpack is listed. Nothing here shows it is waterproof.'),card(),None,None,'How heavy is it?')

def test_unasked_without_message_is_unchanged():
    with pytest.raises(ValueError):
        validate_draft(draft('The Trail Backpack is listed. Nothing here shows it is waterproof.'),card())
