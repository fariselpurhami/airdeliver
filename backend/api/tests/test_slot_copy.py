"""Slot copy renderer: facts come from cards, never from model-typed text. Scripted drafts, no provider call (simulated, not Groq)."""
import json
import pytest
from decimal import Decimal
from tests.test_shopping_discovery_contract import row
from app.services.shopping_discovery import catalog_result
from app.services.shopping_copy import validate_draft
from app.services.conversation.slot_copy import render_slots, SlotError, SLOT_WRITER_RULES

def cards():
    a = catalog_result(row(id=1, name='Studio Headphones', price=Decimal('79.00'), attributes={'connectivity': 'Bluetooth'}))
    b = catalog_result(row(id=2, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}))
    return [a, b]

def ok(text, cs=None, brief=None, message='hi'):
    cs = cs or cards()
    d = render_slots({'text': text}, cs, brief, message)
    validate_draft(d, cs, {}, brief or {}, message)
    return d

def test_slots_render_exact_card_values_and_build_matching_claims():
    d = ok("The [[name:1]] is [[price:1]] and connects by [[spec.connectivity:1]]. I don't have its battery life.")
    assert d.text == "The Studio Headphones is $79.00 and connects by Bluetooth. I don't have its battery life."
    assert d.product_ids == [1]
    assert {(c.field, c.value) for c in d.claims} == {('name', 'Studio Headphones'), ('price', '79.00'), ('spec.connectivity', 'Bluetooth')}

def test_two_products_and_totals_come_from_code():
    d = ok("[[name:1]] is [[price:1]] and [[name:2]] is [[price:2]]. Together that is [[total]], leaving [[left]].", brief={'budget_max': '300'})
    assert '$97.00' in d.text and '$203.00' in d.text and d.product_ids == [1, 2]

@pytest.mark.parametrize('text,reason', [
    ("The [[name:1]] (ID 1) is great", 'slot_literal_fact'),
    ("It costs 79 dollars", 'slot_literal_fact'),
    ("Two days of battery, see https://x.example", 'slot_literal_fact'),
    ("The [[name:9]] is nice", 'slot_unknown_product'),
    ("[[spec.battery:1]] hours", 'slot_spec_unavailable'),
    ("[[price]] total", 'slot_product_missing'),
    ("[[left]] left", 'slot_total_unavailable'),
    ("[[stock:1]] right now", 'slot_stock_not_asked'),
    ("[[colour:1]] is black", 'slot_unknown_kind'),
    ("A broken [[price:1 slot", 'slot_malformed'),
])
def test_unbacked_or_typed_facts_are_rejected(text, reason):
    with pytest.raises(SlotError) as e:
        render_slots({'text': text}, cards(), None, 'hi')
    assert str(e.value) == reason

def test_stock_slot_only_when_the_customer_asked():
    d = ok("Yes, the [[name:1]] is [[stock:1]].", message='is it in stock?')
    assert 'in stock' in d.text and any(c.field == 'stock_status' for c in d.claims)

def test_raw_json_string_and_extra_keys():
    d = render_slots(json.dumps({'text': '[[name:2]] holds [[spec.capacity:2]].'}), cards())
    assert d.text == 'Steel Bottle holds 750 ml.'
    with pytest.raises(SlotError):
        render_slots({'text': 'x', 'claims': []}, cards())

def test_id_leak_and_price_mismatch_are_impossible_by_construction():
    d = ok("Between the [[name:1]] and the [[name:2]], the second one is [[price:2]].")
    assert 'ID' not in d.text and '$18.00' in d.text and 'local_in_stock' not in d.text

def test_writer_rules_forbid_typed_numbers_and_leave_voice_free():
    assert 'Never type a number' in SLOT_WRITER_RULES and 'vary the shape' in SLOT_WRITER_RULES.casefold()


def test_total_needs_two_priced_cards_and_left_needs_a_budget():
    one=cards()[:1]
    with pytest.raises(SlotError):render_slots({'text':'[[total]] together'},one)
    assert render_slots({'text':'[[total]] together'},cards()).text=='$97.00 together'


@pytest.mark.parametrize('text',["It lasts two days on a charge.","Around fifteen hours of battery.","Twenty percent off today.","It holds half a liter","about ten dollars"])
def test_number_words_used_as_facts_are_rejected(text):
    with pytest.raises(SlotError) as e:
        render_slots({'text':text},cards(),None,'hi')
    assert str(e.value)=='slot_number_word_fact'

def test_plain_words_that_are_not_facts_pass():
    assert ok("One thing I do not have is its battery life; the [[name:1]] is the one you asked about.").text.startswith('One thing')


def test_customer_typed_product_words_with_digits_are_echoes_not_facts():
    """Simulated slot draft (n=1 of 8): "PS5" in the customer's own question was rejected as a typed fact."""
    import pytest
    from tests.test_shopping_discovery_contract import row
    from app.services.shopping_discovery import catalog_result
    from app.services.conversation.slot_copy import render_slots, SlotError
    card = catalog_result(row())
    ok = render_slots({'text': "I can't see PS5 support on the [[name:1]], so I won't say yes."}, [card], None, 'Do they work with a PS5?')
    assert 'PS5' in ok.text
    with pytest.raises(SlotError):
        render_slots({'text': "The [[name:1]] works with a PS5 and lasts 30 hours."}, [card], None, 'Do they work with a PS5?')
    with pytest.raises(SlotError):
        render_slots({'text': "It lasts 30h."}, [card], None, 'Does it last 30h?')
    with pytest.raises(SlotError):
        render_slots({'text': "It has PS5 support."}, [card], None, 'Do they work with a PS4?')


def test_plainly_typed_product_name_is_declared_not_withheld():
    """Real Groq (n=1, cmp-03, 1:20 AM): the model typed "Oak Desk" in plain words next to [[total]] and the draft was rejected as an undeclared name."""
    from tests.test_shopping_discovery_contract import row
    from app.services.shopping_discovery import catalog_result
    from app.services.conversation.slot_copy import render_slots
    from app.services.conversation.shopping_copy import validate_draft
    card = catalog_result(row())
    d = render_slots({'text': "Yes, the Studio Headphones fit your plan at [[price:1]]."}, [card], None, 'Do the Studio Headphones fit?')
    assert d.product_ids == [1] and any(c.field == 'name' for c in d.claims)
    validate_draft(d, [card], {}, {}, 'Do the Studio Headphones fit?')


def test_slot_writer_rules_ask_for_sales_engineer_blocks_and_ban_stock_openers():
    """Real Groq (n=1, cmp-03, 2:38 AM): the published slot reply was a bare list opened with a stock phrase, no direct answer, no closing question."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert 'answers the customer' in low and 'one specific, useful question' in low
    assert "here's a rundown" in low and 'sure thing' in low and 'no exclamation' in low
    assert 'never type a number' in low and '[[total]]' in R


def test_slot_writer_rules_forbid_unsupported_ranking_and_praise():
    """Real Groq (n=1, cmp-01, 3:04 AM): "the better choice" and "lightweight pack" were rejected by the real review (supported=false), the whole reply was withheld."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert 'do not rank or praise' in low and 'lightweight' in low and 'ask what matters most' in low


def test_slot_writer_rules_keep_delivery_talk_to_one_plain_refusal():
    """Real Groq (n=1, grd-01, 4:21 AM): "confirm the merchant's shipping schedule" tripped the deterministic policy backstop."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    assert '[[no_promise]]' in R and 'next-day' in R


def test_no_promise_slot_renders_a_fixed_refusal_that_passes_the_policy_backstop():
    """Real Groq (n=1, grd-01, 4:33 AM): the model offered "items with confirmed next-day delivery", which the backstop rightly rejects. The refusal is now code-written."""
    import pytest
    from tests.test_shopping_discovery_contract import row
    from app.services.shopping_discovery import catalog_result
    from app.services.conversation.slot_copy import render_slots, SlotError
    from app.services.conversation.shopping_copy import validate_draft
    card = catalog_result(row())
    q = 'Can you guarantee the Studio Headphones arrive tomorrow?'
    d = render_slots({'text': "[[no_promise]]\n\nThe [[name:1]] is [[price:1]]. Do you need it for a specific date?"}, [card], None, q)
    assert "I can't promise merchant stock or delivery timing." in d.text
    validate_draft(d, [card], {}, {}, q)
    with pytest.raises(SlotError):
        render_slots({'text': '[[no_promise:1]]'}, [card], None, q)


def test_slot_writer_rules_require_consistency_and_specific_unknowns():
    """Real Groq (n=1, hard-01, 5:39 AM): "I don't have details on the Desk Lamp" next to a bullet stating its material; "durable bottle" had no slot behind it. The real review approved it."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert 'never say you lack details' in low and 'list those specific missing things' in low and 'durable' in low
