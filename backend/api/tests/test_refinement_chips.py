"""Quick-tap refinement chips are derived only from listed catalog facts; nothing is invented."""
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result, ShoppingBrief
from app.services.conversation.refinement_chips import refinement_chips

def cards():
    spec=[(1,'Cotton Shirt','24.00','shirts'),(2,'Wool Scarf','30.00','accessories'),(3,'Trail Backpack','59.00','backpacks'),(4,'Studio Headphones','79.00','headphones')]
    return [catalog_result(row(id=i,name=n,sku=f'S{i}',price=Decimal(p),category=c)) for i,n,p,c in spec]

def test_chips_use_only_listed_categories_and_listed_prices():
    chips=refinement_chips(cards(),ShoppingBrief())
    assert chips and len(chips)<=4
    listed={'24.00','30.00','59.00','79.00'}
    cats={'shirts','accessories','backpacks','headphones'}
    for chip in chips:
        assert chip.source_product_ids
        if chip.kind=='category': assert chip.value in cats
        else: assert chip.kind=='price_cap' and chip.value in listed
        assert chip.value in chip.send_text

def test_price_chip_is_skipped_when_customer_already_set_a_budget():
    chips=refinement_chips(cards(),ShoppingBrief(budget_max='100',budget_currency='USD'))
    assert all(c.kind!='price_cap' for c in chips)

def test_no_chips_for_a_single_result_or_unknown_prices():
    assert refinement_chips(cards()[:1],ShoppingBrief())==[]
    assert refinement_chips([],ShoppingBrief())==[]

def test_mixed_currencies_never_make_a_price_chip():
    a,b,c=cards()[:3]
    b=b.model_copy(update={'currency':'EUR'})
    assert all(x.kind!='price_cap' for x in refinement_chips([a,b,c],ShoppingBrief()))

def test_labels_have_no_claims_or_urgency():
    for chip in refinement_chips(cards(),ShoppingBrief()):
        low=(chip.label+chip.send_text).lower()
        assert not any(w in low for w in ('best','perfect','popular','limited','deal','sale','in stock'))
