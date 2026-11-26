"""A draft that names the one asked-about product but declares no product_ids is not a reason to withhold.

Observed on a real Groq draft (n=1, bait-04, low-1200): an honest "country and warranty are not listed" answer
about the Steel Bottle had product_ids=[] and claims=[], and was withheld as undeclared_catalog_name.
The id and name claim come from the card.
"""
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft, declare_sole_named_card

def cards(*names):
    return [catalog_result(row(id=i,name=n,price=Decimal('10.00'),category='bottles')) for i,n in enumerate(names,1)]

def test_sole_named_card_is_declared_with_name_claim_and_passes():
    cs=cards('Steel Bottle')
    d=declare_sole_named_card(ShoppingDraft(text='The Steel Bottle origin is not listed.',product_ids=[],claims=[]),cs)
    assert d.product_ids==[1] and [(c.field,c.value) for c in d.claims]==[('name','Steel Bottle')]
    validate_draft(d,cs)

def test_without_completion_it_is_still_rejected():
    with pytest.raises(ValueError):
        validate_draft(ShoppingDraft(text='The Steel Bottle origin is not listed.',product_ids=[],claims=[]),cards('Steel Bottle'))

def test_two_named_cards_are_left_alone():
    cs=cards('Steel Bottle','Glass Bottle')
    d=ShoppingDraft(text='Steel Bottle or Glass Bottle?',product_ids=[],claims=[])
    assert declare_sole_named_card(d,cs) is d

def test_no_card_named_is_left_alone():
    d=ShoppingDraft(text='Which bottle do you mean?',product_ids=[],claims=[])
    assert declare_sole_named_card(d,cards('Steel Bottle')) is d

def test_a_draft_that_already_declares_a_product_is_left_alone():
    cs=cards('Steel Bottle','Glass Bottle')
    d=ShoppingDraft(text='Steel Bottle and Glass Bottle.',product_ids=[1],claims=[{'product_id':1,'field':'name','value':'Steel Bottle'}])
    assert declare_sole_named_card(d,cs) is d
    with pytest.raises(ValueError):
        validate_draft(d,cs)
