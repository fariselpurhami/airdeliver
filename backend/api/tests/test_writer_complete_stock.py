"""Forgetting the stock_status claim must not withhold an honest "in stock" answer.

Observed on a real Groq draft (n=1, bait-02, low-1200): the draft said the Smart Watch is in stock locally and
was otherwise honest; it was withheld as unclaimed_stock_claim. The claim value comes from the card, not the model.
"""
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft, complete_stock_claims

def cards(*stocks):
    out=[]
    for i,st in enumerate(stocks,1):
        c=catalog_result(row(id=i,name=f'Item {i}',price=Decimal('10.00'),category='bags'))
        out.append(c.model_copy(update={'stock_status':st}))
    return out

def draft(text,ids):
    return ShoppingDraft(text=text,product_ids=ids,claims=[{'product_id':i,'field':'name','value':f'Item {i}'} for i in ids])

def test_in_stock_text_gets_card_stock_claim_and_passes():
    cs=cards('local_in_stock')
    d=complete_stock_claims(draft('Item 1 is in stock locally.',[1]),cs)
    assert [c.value for c in d.claims if c.field=='stock_status']==['local_in_stock']
    validate_draft(d,cs)

def test_unclaimed_without_completion_is_still_rejected():
    with pytest.raises(ValueError):
        validate_draft(draft('Item 1 is in stock locally.',[1]),cards('local_in_stock'))

@pytest.mark.parametrize('stocks',[('local_out_of_stock',),('unverified',),('demo',)])
def test_not_in_stock_card_is_never_completed(stocks):
    cs=cards(*stocks)
    d=complete_stock_claims(draft('Item 1 is in stock.',[1]),cs)
    assert not [c for c in d.claims if c.field=='stock_status']
    with pytest.raises(ValueError):
        validate_draft(d,cs)

def test_mixed_stock_declared_products_are_left_alone():
    cs=cards('local_in_stock','local_out_of_stock')
    d=complete_stock_claims(draft('Item 1 is in stock, Item 2 too.',[1,2]),cs)
    assert not [c for c in d.claims if c.field=='stock_status']

def test_text_without_stock_wording_is_untouched():
    d=draft('Item 1 weighs 650 g.',[1])
    assert complete_stock_claims(d,cards('local_in_stock')) is d

def test_existing_stock_claim_is_untouched():
    d=ShoppingDraft(text='Item 1 is in stock.',product_ids=[1],claims=[{'product_id':1,'field':'stock_status','value':'local_in_stock'}])
    assert complete_stock_claims(d,cards('local_in_stock')) is d
