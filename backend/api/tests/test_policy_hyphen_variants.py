"""A typographic hyphen must not hide a delivery or shipping promise from the deterministic backstop.
Found by a real Groq run (n=1, grd-01, 4:21 AM) that wrote "next\u2011day" with a non-breaking hyphen."""
import pytest
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import validate_draft, ShoppingDraft


def d(text):
    return ShoppingDraft.model_validate({'text': text, 'product_ids': [1], 'claims': [{'product_id': 1, 'field': 'name', 'value': 'Studio Headphones'}]})


@pytest.mark.parametrize('dash', ['-', '\u2010', '\u2011', '\u2013'])
def test_next_day_promise_is_caught_with_any_hyphen(dash):
    card = catalog_result(row())
    with pytest.raises(ValueError):
        validate_draft(d(f'The Studio Headphones come with next{dash}day delivery.'), [card], {}, {}, 'Tell me about them')
