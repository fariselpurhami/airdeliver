"""One honest negation may cover a short coordinated list; it must never cover a separate affirmative clause."""
import pytest
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft

NAME={'product_id':1,'field':'name','value':'Studio Headphones'}

def draft(text):
    return ShoppingDraft(text=text,product_ids=[1],claims=[NAME])

@pytest.mark.parametrize('text',[
 'Studio Headphones: warranty and return terms are not listed, so I cannot confirm them.',
 'Studio Headphones list no warranty details; free shipping and refunds are not listed either.',
 'For Studio Headphones, free shipping or easy returns are not mentioned in the catalog.',
])
def test_one_negation_covers_a_short_coordinated_list(text):
    validate_draft(draft(text),[catalog_result(row())])

@pytest.mark.parametrize('text',[
 'Studio Headphones come with free shipping and the catalog does not list returns.',
 'Studio Headphones have a warranty and the catalog is not clear on stock.',
 'Studio Headphones include free shipping and refunds are not listed.',
 'Studio Headphones come with a warranty and returns are easy.',
 'Studio Headphones have free shipping and return terms are not only generous.',
])
def test_negation_never_covers_a_separate_affirmative_clause(text):
    with pytest.raises(ValueError):
        validate_draft(draft(text),[catalog_result(row())])
