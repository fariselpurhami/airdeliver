"""Writer prose must not state commercial facts that have no exact claim."""
import pytest
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft

NAME={'product_id':1,'field':'name','value':'Studio Headphones'}

def draft(text,claims=()):
    return ShoppingDraft(text=text,product_ids=[1],claims=[NAME,*claims])

@pytest.mark.parametrize('text',[
 'Studio Headphones are in stock and ready to ship.',
 'Studio Headphones come with free shipping and next day delivery.',
 'Studio Headphones have a two year warranty and easy returns.',
 'Studio Headphones are the best choice and a perfect fit for you.',
 'Studio Headphones are waterproof and noise cancelling.',
])
def test_unclaimed_commercial_or_spec_fact_is_rejected(text):
    card=catalog_result(row())
    with pytest.raises(ValueError):validate_draft(draft(text),[card])

def test_claimed_facts_and_unknown_wording_still_pass():
    card=catalog_result(row(attributes={'battery':'48 hours'}))
    validate_draft(draft('Studio Headphones list battery as 48 hours; fit details are unknown.',
        [{'product_id':1,'field':'spec.battery','value':'48 hours'}]),[card])
    validate_draft(draft('Studio Headphones are listed locally; merchant stock is not verified.'),[card])
