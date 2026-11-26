"""The customer's own budget cap may be echoed as 'under $N' only when it cannot become a false price claim."""
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft

def claims(i,price): return [{'product_id':i,'field':'name','value':'Wool Scarf'},{'product_id':i,'field':'price','value':price}]
def card(price='30.00'): return catalog_result(row(id=1,name='Wool Scarf',price=Decimal(price),category='accessories'))
def d(text,price='30.00'): return ShoppingDraft(text=text,product_ids=[1],claims=claims(1,price))
BRIEF={'budget_max':'100'}

@pytest.mark.parametrize('text',[
 'For a gift under $100, I would start with Wool Scarf at 30.00 USD.',
 'Wool Scarf is listed at 30.00 USD, well within $100 as you asked.',
 'I looked for options up to 100 USD, and Wool Scarf is listed at 30.00 USD.',
])
def test_echoing_the_customer_cap_passes_when_every_named_product_is_within_it(text):
    validate_draft(d(text),[card()],None,BRIEF)

@pytest.mark.parametrize('text,price',[
 ('For a gift under $100, I would start with Wool Scarf at 120.00 USD.','120.00'),
 ('Wool Scarf is listed at 120.00 USD, well within $100.','120.00'),
 ('For a gift under $50, I would start with Wool Scarf at 30.00 USD.','30.00'),
 ('For a gift over $100, I would start with Wool Scarf at 30.00 USD.','30.00'),
])
def test_cap_echo_never_launders_a_false_or_different_number(text,price):
    with pytest.raises(ValueError,match='unsupported_numeric_or_link_claim'):
        validate_draft(d(text,price),[card(price)],None,BRIEF)
