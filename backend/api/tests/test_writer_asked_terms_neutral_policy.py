"""Neutral mentions and policy words the customer asked about.

Observed on real Groq drafts (n=1 each): bait-01 ("if you need ... confirmed waterproofing, could you share...")
and bait-04 ("warranty details aren't provided", "no warranty information appears") were honest and withheld.
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
ASK='How many liters is the Trail Backpack and is it waterproof?'
WARR='What is the warranty on the Trail Backpack?'

@pytest.mark.parametrize('text',[
    'The Trail Backpack is listed. Waterproofing is unknown. If you need confirmed waterproofing, tell me your priority.',
    'The Trail Backpack is listed. There is no indication that it is waterproof. Is waterproofing essential for you?',
])
def test_neutral_mention_next_to_a_stated_absence_passes(text):
    validate_draft(draft(text),card(),None,None,ASK)

@pytest.mark.parametrize('text',[
    'The Trail Backpack is listed. The warranty details aren\u2019t provided.',
    'The Trail Backpack is listed. No warranty information appears in the specifications.',
])
def test_asked_policy_word_with_absence_passes(text):
    validate_draft(draft(text),card(),None,None,WARR)

@pytest.mark.parametrize('text,ask',[
    ('The Trail Backpack is listed. If you need rain gear, it is waterproof.',ASK),
    ('The Trail Backpack is listed. If you want it, it is waterproof.',ASK),
    ('The Trail Backpack comes with a warranty.',WARR),
    ('The Trail Backpack is listed. Capacity is not listed, and it comes with a warranty.',WARR),
    ('The Trail Backpack is listed. No problem, there is a warranty.',WARR),
    ('The Trail Backpack is listed. The warranty is not listed, but it ships next-day.',WARR),
    ('The Trail Backpack is listed. It ships free.','Is there a warranty?'),
])
def test_affirmative_claims_still_rejected(text,ask):
    with pytest.raises(ValueError):
        validate_draft(draft(text),card(),None,None,ask)

def test_offer_of_an_alternative_with_the_asked_term_passes():
    validate_draft(draft('The Trail Backpack is listed. Warranty details are not provided. Let me know if you would like help finding another bag with a stated warranty.'),card(),None,None,WARR)

def test_alternative_wording_does_not_excuse_an_affirmative_claim():
    with pytest.raises(ValueError):
        validate_draft(draft('The Trail Backpack is listed. Another option: this one has a warranty.'),card(),None,None,WARR)
