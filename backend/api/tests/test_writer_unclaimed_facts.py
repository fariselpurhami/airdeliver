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


@pytest.mark.parametrize('text',[
 'Studio Headphones do not list a warranty, so I cannot confirm one.',
 'Free shipping is not listed for Studio Headphones.',
 'Next-day delivery is not verified for Studio Headphones.',
 'The catalog does not specify whether Studio Headphones are waterproof.',
 'I cannot say Studio Headphones are the best one.',
 'Studio Headphones: warranty details are unknown.',
])
def test_honest_not_listed_wording_about_policy_terms_is_allowed(text):
    validate_draft(draft(text),[catalog_result(row())])

@pytest.mark.parametrize('text',[
 'Studio Headphones do not list battery life but come with free shipping.',
 'Warranty is not listed, yet Studio Headphones ship free.',
 'Not only a warranty, Studio Headphones include free shipping.',
 'Studio Headphones are not cheap, but they are waterproof.',
 'No shipping fees apply to Studio Headphones.',
 'Studio Headphones are not out of stock and come with a two year warranty.',
 'The catalog does not list it. Studio Headphones have a warranty.',
 'Not listed: Studio Headphones are the best.',
 'Studio Headphones are not waterproof.',
 'Studio Headphones do not provide waterproof protection.',
])
def test_negation_cannot_launder_an_affirmative_commercial_claim(text):
    with pytest.raises(ValueError):validate_draft(draft(text),[catalog_result(row())])
