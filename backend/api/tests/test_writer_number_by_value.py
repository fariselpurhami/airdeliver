"""A grounded price written without trailing zeros must match its exact claim by value."""
import pytest
from tests.test_shopping_discovery_contract import row
from decimal import Decimal
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft

NAME={'product_id':1,'field':'name','value':'Cotton Shirt'}
PRICE={'product_id':1,'field':'price','value':'24.00'}

def draft(text):
    return ShoppingDraft(text=text,product_ids=[1],claims=[NAME,PRICE])

def card():
    return catalog_result(row(name='Cotton Shirt',price=Decimal('24.00')))

@pytest.mark.parametrize('text',[
 'Cotton Shirt is listed at $24.',
 'Cotton Shirt is listed at $24.00.',
 'Cotton Shirt is listed at 24 USD.',
 'Cotton Shirt is listed at 24.0 dollars.',
])
def test_same_value_price_with_different_formatting_passes(text):
    validate_draft(draft(text),[card()])

@pytest.mark.parametrize('text',[
 'Cotton Shirt is listed at $25.',
 'Cotton Shirt is listed at $2.4.',
 'Cotton Shirt is listed at $240.',
 'Cotton Shirt is listed at $24 and $19.',
 'Cotton Shirt is listed at $24.01.',
])
def test_different_value_still_rejected(text):
    with pytest.raises(ValueError,match='unsupported_numeric_or_link_claim'):
        validate_draft(draft(text),[card()])
