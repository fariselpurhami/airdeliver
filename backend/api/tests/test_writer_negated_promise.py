"""An honest refusal to promise ("I can't promise next-day arrival") is not a fulfillment promise.

Observed once on a real Groq draft (n=1): an honest decline was withheld only because the negation list
had no promise/assure verbs. Affirmative promises and a negation in another clause stay rejected.
"""
import pytest
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft

NAME={'product_id':1,'field':'name','value':'Studio Headphones'}
def draft(text): return ShoppingDraft(text=text,product_ids=[1],claims=[NAME])
def check(text): validate_draft(draft(text),[catalog_result(row())])


@pytest.mark.parametrize('text',[
 "Studio Headphones: I can't promise next-day arrival.",
 'Studio Headphones: I cannot promise same-day or next-day delivery.',
 "Studio Headphones: I can't assure next-day arrival or free shipping.",
 "Studio Headphones: we don't promise next-day delivery from the catalog data.",
])
def test_honest_refusal_to_promise_is_accepted(text):
    check(text)


@pytest.mark.parametrize('text',[
 'Studio Headphones: I promise next-day delivery.',
 'Studio Headphones: next-day arrival is promised.',
 "Studio Headphones: I can't promise much, but they ship free.",
 "Studio Headphones: I can't promise a refund and they offer next-day delivery.",
 'Studio Headphones: we assure you of free shipping.',
])
def test_affirmative_promises_and_other_clauses_stay_rejected(text):
    with pytest.raises(ValueError,match='unclaimed_fulfillment_or_policy_claim'):
        check(text)
