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
    assert 'answer their actual question first' in low and 'one specific question' in low
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


def test_value_typed_right_before_its_own_slot_is_dropped_not_rejected():
    """Real Groq (n=1, hard-01, 6:30 AM): "weighs 650 g [[spec.weight:2]]" and "holds 750 ml [[name:5]] [[spec.capacity:5]]" were rejected as typed facts and the reply fell back to the old writer, which was withheld. A typed value equal to the slot's own value is a redundant echo; any other typed value is still rejected."""
    d = ok("The [[name:2]] holds 750 ml [[spec.capacity:2]] for a day out.")
    assert d.text == "The Steel Bottle holds 750 ml for a day out."
    assert d.text.count('750 ml') == 1
    with pytest.raises(SlotError):
        ok("The [[name:2]] holds 500 ml [[spec.capacity:2]].")
    with pytest.raises(SlotError):
        ok("The [[name:2]] holds 750 ml of water [[name:1]].")
    d2 = ok("It is made of Bluetooth [[spec.connectivity:1]], the [[name:1]].")
    assert d2.text.count('Bluetooth') == 1


def test_typed_card_value_in_a_one_product_line_becomes_its_slot():
    """Real Groq (n=1, hard-01, 7:09 AM): "Steel Bottle holds 750 ml and costs [[price:2]]" was rejected as a typed fact and the reply fell to the weaker old writer. When a line is about exactly one product and the typed value equals that product's own card spec, it is rendered from the slot. Other lines and values are still rejected."""
    d = ok("- Steel Bottle holds 750 ml and costs [[price:2]].\n- The [[name:1]] connects by Bluetooth.")
    assert "Steel Bottle holds 750 ml and costs $18.00." in d.text and "connects by Bluetooth." in d.text
    assert {(c.product_id, c.field) for c in d.claims} >= {(2, 'spec.capacity'), (1, 'spec.connectivity')}
    with pytest.raises(SlotError):
        ok("The [[name:2]] and the [[name:1]] both hold 750 ml.")
    with pytest.raises(SlotError):
        ok("- Steel Bottle holds 900 ml and costs [[price:2]].")
    with pytest.raises(SlotError):
        ok("- Studio Headphones hold 750 ml.")


def test_value_typed_then_cited_with_name_and_spec_slots_renders_once():
    """Real Groq (n=1, hard-01, 7:21 AM, published and review-approved): "weighs about 650 g [[name:2]] [[spec.weight:2]]" rendered as "weighs about 650 g Trail Backpack 650 g". The tail pair is a citation of a value already typed; it is removed so the value shows once. A line that still repeats a value is rejected."""
    d = ok("- Steel Bottle holds about 750 ml of liquid [[name:2]] [[spec.capacity:2]]\n- The [[name:1]] connects by Bluetooth [[name:1]] [[spec.connectivity:1]]")
    assert d.text == "- Steel Bottle holds about 750 ml of liquid\n- The Studio Headphones connects by Bluetooth"
    assert {(c.product_id, c.field) for c in d.claims} >= {(2, 'spec.capacity'), (1, 'spec.connectivity')}
    with pytest.raises(SlotError):
        ok("The [[name:1]] connects by [[spec.connectivity:1]] and again [[spec.connectivity:1]].")

def test_slot_writer_rules_ask_for_depth_personality_and_a_trade_off_without_new_facts():
    """User (7:26 AM): replies were too short, too generic and not AI-native; he wants a human sales engineer with a voice and a deeper narrative. Prompt-level only: whether the free model delivers it is measured with real runs, not by this test."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert '120 to 220 words' in low and 'length follows the data' in low and 'trade-off' in low and 'contractions' in low and 'situation' in low
    assert 'never add a fact, number or feature' in low and 'do not reuse a fixed template' in low


def test_slot_writer_rules_ban_guessed_implications_and_valueless_bullets():
    """Real Groq (n=1, cmp-01, 7:31 AM, draft only): "its weight is the only weight spec we have, so you know it's fairly light" and a bullet "provides a weight spec" with no value."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert 'do not guess what a value implies' in low and 'every bullet must carry at least one slot value' in low


def _rich(pid=7, **kw):
    return catalog_result(row(id=pid, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, **kw))


def test_source_description_tags_and_rating_reach_slot_cards_only_when_real():
    """Audit (7:43 AM): the importer and the Product table keep description, tags and rating from the authorised source, but CatalogResult dropped them, so the writer saw name, category, price and attributes only."""
    from app.services.conversation.slot_copy import enrich_cards
    rich = _rich(description='Padded 30 L daypack for day hikes. Ships in a box.', tags=['hiking', 'outdoor'], rating=4.6)
    plain = _rich(9)
    assert 'description' not in rich.model_dump() and 'rating' not in rich.model_dump()  # API and old writer payloads are unchanged
    e = enrich_cards([rich, plain])
    assert e[0].catalog_specs['description'] == 'Padded 30 L daypack for day hikes.'
    assert e[0].catalog_specs['rating'] == '4.6 out of 5' and e[0].catalog_specs['tags'] == 'hiking, outdoor'
    assert e[0].catalog_specs['weight'] == '650 g'
    assert e[1].catalog_specs == {'weight': '650 g'}
    clash = enrich_cards([catalog_result(row(id=8, name='Lamp', attributes={'rating': 'house brand'}, rating=3.0))])[0]
    assert clash.catalog_specs['rating'] == 'house brand'
    d = ok("The [[name:7]] is described as: [[spec.description:7]] Rated [[spec.rating:7]].", cs=e)
    assert 'Padded 30 L daypack for day hikes.' in d.text and '4.6 out of 5' in d.text


def test_slot_writer_rules_scale_length_to_data_and_ban_general_knowledge():
    """Real Groq (n=1, cmp-01, 7:49 AM): with one spec per product the 120 to 220 word target produced a padded draft that restated the same unknowns three times and claimed "a lighter pack means less strain"; the real review rejected it."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert '60 to 110 words' in low and 'never restate a missing fact twice' in low and 'general knowledge' in low

def test_a_fact_slot_after_another_products_name_in_the_same_sentence_is_rejected():
    """Offline proof for the sparse-vs-rich comparison (simulated): "The [[name:2]] has a [[spec.rating:5]] rating" and "[[name:5]] is a [[spec.description:2]]" rendered another product's fact under the wrong name. Comparisons that name each product before its own facts still pass."""
    cs = cards()
    with pytest.raises(SlotError):
        ok("The [[name:1]] weighs [[spec.capacity:2]].", cs=cs)
    with pytest.raises(SlotError):
        ok("Steel Bottle costs [[price:1]].", cs=cs)
    d = ok("The [[name:1]] is [[price:1]], while the [[name:2]] holds [[spec.capacity:2]]. Which matters more?", cs=cs)
    assert 'Studio Headphones is $79.00' in d.text and '750 ml' in d.text
    d2 = ok("The [[name:1]] is [[price:1]]. The [[name:2]] is [[price:2]].", cs=cs)
    assert d2.product_ids == [1, 2]
