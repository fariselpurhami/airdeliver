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


CLOSERS = ('These do different jobs, so which one are you actually after: {a} or {b}?', 'Since they do different jobs, which one do you actually want: {a} or {b}?', 'They cover different needs, so which are you after: {a} or {b}?')
KINDS = ('so they look like two different kinds of item, not substitutes.', 'so they are not interchangeable.', 'so they are not really alternatives to each other.')

def closer_in(text, a, b):
    return any(c.format(a=a, b=b) in text for c in CLOSERS)

def kind_in(text, first):
    return any(first + k in text for k in KINDS)

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


def test_slot_writer_rules_forbid_paraphrasing_descriptions_and_praising_ratings():
    """Real Groq comparison (n=1, rich synthetic cards, 8:34 AM): the draft paraphrased the description ("a padded 30 L compartment and rain cover", "keeps drinks cold for a full day") with typed numbers, so the renderer rejected it (slot_literal_fact), and it called ratings "solid"."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    low = R.casefold()
    assert 'never restate a description in your own words' in low and 'do not call ratings solid' in low


def test_card_slot_prints_every_listed_fact_exactly_and_declares_claims():
    """Real Groq (n=1, rich synthetic cards, 9:11 AM): the model restated the description in its own words next to the description slot, and the draft was rejected. [[card:ID]] prints the product's name, price, specs, rating, tags and description from the card, so there is nothing left to paraphrase."""
    from app.services.conversation.slot_copy import enrich_cards
    rich = catalog_result(row(id=7, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded daypack with a rain cover. Ships in a box.', tags=['hiking', 'outdoor'], rating=4.5))
    cs = enrich_cards([rich, cards()[1]])
    d = ok("The pack looks right for a day on the trail.\n\n- [[card:7]]\n- [[card:2]]\n\nWhich matters more to you?", cs=cs)
    assert "- Trail Backpack\n  - Price: $59.00\n  - Weight: 650 g\n  - Rating: 4.5 out of 5\n  - Tags: hiking, outdoor\n  - Description: Padded daypack with a rain cover.\n" in d.text
    assert "- Steel Bottle\n  - Price: $18.00\n  - Capacity: 750 ml\n" in d.text
    assert {(c.product_id, c.field) for c in d.claims} >= {(7, 'name'), (7, 'price'), (7, 'spec.weight'), (7, 'spec.rating'), (7, 'spec.description'), (2, 'spec.capacity')}
    with pytest.raises(SlotError):
        ok("- [[card:99]]", cs=cs)
    with pytest.raises(SlotError):
        ok("- [[card]]", cs=cs)


def test_sentences_with_typed_facts_are_dropped_not_the_whole_draft():
    """Real Groq (n=1, rich synthetic cards, 9:24 AM): a sound draft with the [[card]] bullets was rejected as a whole because one sentence said "the backpack's 30 L volume (from its description)". Only that sentence goes (content is removed, never added); more than two dropped sentences still rejects the draft."""
    cs = cards()
    d = ok("The [[name:1]] suits a commute.\nIts 30 hour battery lasts a week. It is quiet on the train.\n\n- [[card:1]]\n\nWhich matters more to you?", cs=cs)
    assert 'battery' not in d.text and 'quiet on the train' in d.text and 'Which matters more to you?' in d.text and '\n\n\n' not in d.text
    with pytest.raises(SlotError):
        ok("The [[name:1]] is 5 inches wide. It weighs 3 kg. It lasts 9 hours. Do you like it?", cs=cs)
    with pytest.raises(SlotError):
        ok("Visit www.example.com for the [[name:1]].", cs=cs)


def test_slot_writer_rules_do_not_mention_warranty_or_returns_unprompted():
    """Real Groq (n=1, rich synthetic cards, 9:24 AM): "I do not know about any warranty or return options" tripped the policy backstop and withheld an otherwise sound draft."""
    from app.services.conversation.slot_copy import SLOT_WRITER_RULES as R
    assert 'never mention warranty, returns, shipping, delivery or guarantees' in R.casefold()


def test_mask_payload_hides_values_and_leaves_tokens_original_untouched():
    """Masked slot mode: the model must have no digits or description words to copy; the real payload is not mutated and the tokens render back to the exact card values."""
    from app.services.conversation.slot_copy import enrich_cards, mask_payload
    rich = catalog_result(row(id=7, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded 30 L daypack.', tags=['hiking'], rating=4.5))
    cs = enrich_cards([rich])
    payload = {'task': 'catalog_results', 'catalog_evidence': [c.model_dump(mode='json', exclude={'image', 'sku', 'attributes'}) for c in cs], 'exact_totals': {'total': '59.00'}}
    masked = mask_payload(payload)
    dumped = json.dumps(masked)
    for leaked in ('59.00', '650', '30 L', 'Padded', '4.5', 'hiking'):
        assert leaked not in dumped
    assert '[[price:7]]' in dumped and '[[spec.weight:7]]' in dumped and '[[spec.description:7]]' in dumped
    assert payload['catalog_evidence'][0]['price'] == '59.00'
    d = ok('The pack [[name:7]] is [[price:7]] and [[spec.weight:7]].\n\nWhich matters more?', cs=cs)
    assert '$59.00' in d.text and '650 g' in d.text


def test_compose_builds_facts_from_cards_and_model_supplies_only_opening_and_question():
    """Compose mode: four real drafts (n=4, rich synthetic cards) leaked card values or went generic. Code writes every fact, gap and one-sided comparison; the model's two pieces must carry no digits."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    rich = catalog_result(row(id=7, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded daypack with a rain cover.', tags=['hiking'], rating=4.5))
    cs = enrich_cards([rich, cards()[1]])
    text = compose_text('Two different jobs on a hike, so it depends what you need to carry.', 'Which matters more, carrying gear or drinks?', cs)
    d = ok(text, cs=cs)
    assert d.text.startswith('Two different jobs')
    assert '- Trail Backpack\n  - Price: $59.00\n  - Weight: 650 g' in d.text
    # User review (14:58): nobody asked about weight or capacity, so the gap paragraph is not shown.
    assert 'no separate' not in d.text and 'cannot be compared directly' not in d.text
    gap = ok(compose_text('Okay.', 'Which?', cs, 'What is the weight of each?'), cs=cs, message='What is the weight of each?')
    assert 'Steel Bottle has no separate weight entry.' in gap.text and 'no separate capacity' not in gap.text
    assert 'no listed' not in gap.text and 'Check each description for anything beyond these entries.' in gap.text
    assert closer_in(d.text.rstrip().split('\n\n')[-1], 'Trail Backpack', 'Steel Bottle')  # code-built question for different kinds (15:17)
    leaked = ok(compose_text('The pack holds 30 L.', 'Which?', cs), cs=cs)
    assert 'holds 30 L' not in leaked.text


def test_compose_rejects_model_text_that_paraphrases_card_descriptions_or_tags():
    """Real n=1 (slot path, 9:57): "the bottle's double-wall vacuum design means your drinks stay cold" has no digit, so the typed-fact guard passed it. In compose mode the model's two pieces may not reuse description, tag or spec words the customer did not use."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    rich = catalog_result(row(id=7, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded daypack with a ventilated back panel and a rain cover.', tags=['hiking', 'daypack'], rating=4.5))
    cs = enrich_cards([rich, cards()[1]])
    msg = 'Which is better for a weekend hike?'
    with pytest.raises(SlotError):
        compose_text('The pack has a ventilated back panel, so it suits long walks.', 'Which matters more?', cs, msg)
    with pytest.raises(SlotError):
        compose_text('Two options.', 'Do you want a padded carry option?', cs, msg)
    assert 'weekend hike' in compose_text('Two options for a weekend hike, for different jobs.', 'Which matters more?', cs, msg)


def test_compose_adds_a_fit_line_only_where_a_card_tag_matches_the_customers_own_word():
    """Thin advice in compose mode: code may say which product is tagged for what the customer asked (a card fact matched to the customer's own word), and nothing else."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    rich = catalog_result(row(id=7, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded daypack.', tags=['hiking', 'daypack'], rating=4.5))
    cs = enrich_cards([rich, cards()[1]])
    d = ok(compose_text('Two options here.', 'Which matters more?', cs, 'Which is better for a weekend hike?'), cs=cs, message='Which is better for a weekend hike?')
    assert 'For "hike": Trail Backpack is tagged hiking.' in d.text  # the other card lists no tags, so no claim about it
    assert 'You mentioned' not in d.text
    quiet = ok(compose_text('Two options here.', 'Which matters more?', cs, 'Which is better for a commute?'), cs=cs, message='Which is better for a commute?')
    assert 'is tagged' not in quiet.text


def test_compose_fit_line_and_model_pieces_survive_wider_stress():
    """Offline stress (mocked pieces, 4 card sets x 3 questions): a tag equal to the customer's word repeated the value in one line (slot_duplicate_value), and a model question that offers free delivery or asks about warranty must be rejected in code."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    lamp = catalog_result(row(id=1, name='Desk Lamp', price=Decimal('35.00'), attributes={'material': 'aluminium'}, description='Adjustable arm lamp.', tags=['office'], rating=4.2))
    cs = enrich_cards([lamp])
    msg = 'Which one for my home office?'
    d = ok(compose_text('Here is the lamp.', 'What matters most to you?', cs, msg), cs=cs, message=msg)
    assert 'Desk Lamp is tagged office' in d.text and 'which matches your question' in d.text
    for bad in ('Do you want free delivery?', 'Does it need a warranty or easy returns?', 'Should I reserve one for you?'):
        with pytest.raises(SlotError):
            compose_text('Okay.', bad, cs, msg)

    chair = catalog_result(row(id=2, name='Office Chair', price=Decimal('120.00'), attributes={'weight': '9 kg'}, tags=['office']))
    both = enrich_cards([lamp, chair])
    ok(compose_text('Okay.', 'What matters most to you?', both, msg), cs=both, message=msg)


def test_compose_question_may_use_a_tag_word_but_not_description_words():
    """Real n=1 (11:51): the question "staying hydrated on your weekend hikes" was rejected because a tag says hydration, and the reply fell back to the old writer and was withheld. Tags are category words; features live in the description."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    rich = catalog_result(row(id=7, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}, description='Double-wall vacuum bottle.', tags=['hydration', 'insulated']))
    cs = enrich_cards([rich])
    msg = 'Which is better for a weekend hike?'
    assert 'staying hydrated' in compose_text('Okay.', 'Do you care about staying hydrated on the trail?', cs, msg)
    with pytest.raises(SlotError):
        compose_text('The hydration pick helps.', 'Which?', cs, msg)
    with pytest.raises(SlotError):
        compose_text('Okay.', 'Do you want the vacuum design?', cs, msg)


def test_compose_states_the_fact_that_answers_what_the_customer_asked_for():
    """Compose needed a clearer recommendation. Code may say which card lists the lowest price, highest rating or lowest weight, but only when the customer asked for that, only from listed values, and only through slots."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    a = catalog_result(row(id=1, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded daypack.', tags=['hiking'], rating=4.5))
    b = catalog_result(row(id=2, name='Day Pack', price=Decimal('45.00'), attributes={'weight': '1.2 kg'}, description='Simple pack.', tags=['city'], rating=4.7))
    cs = enrich_cards([a, b])
    def go(msg):
        return ok(compose_text('Okay.', 'What matters most to you?', cs, msg), cs=cs, message=msg).text
    assert 'On price, Day Pack is the lowest listed at $45.00; next is Trail Backpack at $59.00.' in go('Which is the cheapest?')
    assert 'On rating, Day Pack lists the highest: 4.7 out of 5. Trail Backpack lists 4.5 out of 5.' in go('Which has the best rating?')
    assert 'On weight, Trail Backpack lists the lowest: 650 g. Day Pack lists 1.2 kg.' in go('Which is the lightest?')
    plain = go('Tell me about these')
    assert 'On price' not in plain and 'On rating' not in plain and 'On weight' not in plain


def test_compose_puts_the_answer_before_the_fact_blocks_and_varies_the_heading():
    """Advisor feel: when code has a fact that answers the ask, it comes right after the opening, before the long fact blocks. The block heading varies by message (stable per message), not a fixed template."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    a = catalog_result(row(id=1, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}))
    b = catalog_result(row(id=2, name='Day Pack', price=Decimal('45.00'), attributes={'weight': '1.2 kg'}))
    cs = enrich_cards([a, b])
    text = compose_text('Okay.', 'What matters most to you?', cs, 'Which is the cheapest?')
    assert text.index('On price') < text.index('[[cardnp:1]]')
    seen = {compose_text('Okay.', 'Which?', cs, m).split('\n\n')[1] for m in ('one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight')}
    assert len(seen) >= 2
    assert compose_text('Okay.', 'Which?', cs, 'one') == compose_text('Okay.', 'Which?', cs, 'one')
    ok(text, cs=cs, message='Which is the cheapest?')


def test_compose_policy_wording_guard_does_not_trip_on_the_verb_offer():
    """Real n=1 (12:24, cmp-02 commute): "each offering a different way to enjoy the ride" was rejected by the offer* word guard and the reply was withheld. Only promotional wording is blocked."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    cs = enrich_cards(cards())
    assert 'offering a different way' in compose_text('Both are options, each offering a different way to enjoy the ride.', 'Which matters more?', cs, 'Compare these for a commute.')
    for bad in ('Want a special offer?', 'Any promo code or coupon?', 'Want a deal on both?'):
        with pytest.raises(SlotError):
            compose_text('Okay.', bad, cs, 'Compare these for a commute.')


def test_compose_rules_keep_the_question_to_the_customers_own_topics():
    """Real n=1 (12:38, cmp-02): the question "listening to music or tracking your activity" named uses (music, activity tracking) that neither the cards nor the message mention; the grounding review answered supported=false and fulfills_discovery_task=false."""
    from app.services.conversation.slot_copy import COMPOSE_RULES as R
    low = R.casefold()
    assert 'only about topics the customer wrote' in low and 'never name a use or feature the customer did not mention' in low


def test_compose_question_cannot_ask_about_a_field_no_card_lists():
    """Real n=1 (13:51, cmp-02): the question asked about "the weight of the device" while neither card lists a weight."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    cs = enrich_cards(cards())
    with pytest.raises(SlotError):
        compose_text('Okay.', 'Which matters more, the price or the weight?', cs, 'Compare these.')
    assert closer_in(compose_text('Okay.', 'Which matters more, the price or the connectivity?', cs, 'Compare these.'), '[[name:1]]', '[[name:2]]') or 'which' in compose_text('Okay.', 'Which matters more, the price or the connectivity?', cs, 'Compare these.')  # listed-field question passes the guard; different kinds then use the code-built question
    heavy = enrich_cards([catalog_result(row(id=7, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}))])
    assert 'weight' in compose_text('Okay.', 'Is the weight important?', heavy, 'Compare these.')


def test_compose_customer_experience_review_points():
    """User review of the real 14:51 reply (cheapest for a weekend hike): too long (price said twice), a confusing capacity/weight gap paragraph nobody asked for, a backpack and a bottle presented as competitors, a mechanical "You mentioned hike" line that left the bottle unexplained, and a generic closing question."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text, COMPOSE_RULES
    pack = catalog_result(row(id=2, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, description='Padded 30 L daypack.', tags=['hiking', 'daypack', 'outdoor'], rating=4.5))
    bottle = catalog_result(row(id=5, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}, description='Double-wall vacuum bottle.', tags=['hydration', 'insulated', 'outdoor'], rating=4.7))
    cs = enrich_cards([pack, bottle])
    msg = 'Which is the cheapest for a weekend hike, the Trail Backpack or the Steel Bottle?'
    d = ok(compose_text('You want the cheapest option for a hike.', 'Which do you need?', cs, msg), cs=cs, message=msg)
    text = d.text
    assert 'On price, Steel Bottle is the lowest listed at $18.00' in text
    assert text.count('$18.00') == 1 and text.count('$59.00') == 1  # (1) the asked field is not repeated in the blocks
    assert 'no separate' not in text and 'cannot be compared directly' not in text  # (2)
    assert kind_in(text, 'Trail Backpack is listed with weight and Steel Bottle with capacity, ')  # (3)
    assert 'You mentioned' not in text  # (4)
    assert 'For "hike":\n- Trail Backpack is tagged hiking.\n- Steel Bottle has no matching tag (its tags: hydration, insulated, outdoor).' in text
    assert 'ask which of them the customer actually needs' in COMPOSE_RULES.casefold() and 'only factor' in COMPOSE_RULES.casefold()  # (5)
    same = enrich_cards([catalog_result(row(id=1, name='Mug A', price=Decimal('8.00'), attributes={'capacity': '300 ml'})), catalog_result(row(id=2, name='Mug B', price=Decimal('9.00'), attributes={'capacity': '350 ml'}))])
    assert 'different kinds of item' not in compose_text('Okay.', 'Which?', same, 'Compare these mugs.')


def test_compose_different_kinds_get_a_code_built_which_do_you_need_question():
    """User (15:17): yes to a code-built question when the products are different kinds of item, so the reply does not depend on the model noticing. Built from card names only; the model's question is still policy-checked but replaced."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    pack = catalog_result(row(id=2, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, tags=['hiking']))
    bottle = catalog_result(row(id=5, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}, tags=['hydration']))
    cs = enrich_cards([pack, bottle])
    msg = 'Which is the cheapest for a weekend hike?'
    d = ok(compose_text('You want the cheapest option.', 'How important is the weight of the gear?', cs, msg), cs=cs, message=msg)
    assert closer_in(d.text.rstrip().split('\n\n')[-1], 'Trail Backpack', 'Steel Bottle')
    assert 'How important is the weight' not in d.text
    with pytest.raises(SlotError):
        compose_text('Okay.', 'Do you want free delivery?', cs, msg)
    same = enrich_cards([catalog_result(row(id=1, name='Mug A', price=Decimal('8.00'), attributes={'capacity': '300 ml'})), catalog_result(row(id=2, name='Mug B', price=Decimal('9.00'), attributes={'capacity': '350 ml'}))])
    t = compose_text('Okay.', 'Which capacity matters more?', same, 'Compare these mugs.')
    assert t.rstrip().endswith('Which capacity matters more?')


def test_compose_three_products_and_shared_tags_do_not_trip_the_duplicate_value_guard():
    """Offline stress at 18:35 found two crashes on main (SlotError slot_duplicate_value): three products, and two same-kind products sharing the matched tag, because the fit sentences repeated the tag value on one line. Each card gets its own line under one lead-in."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    r = lambda **k: catalog_result(row(**k))
    three = enrich_cards([r(id=1, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, tags=['hiking']), r(id=2, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}, tags=['hydration']), r(id=3, name='Trail Socks', price=Decimal('12.00'), attributes={'material': 'wool'}, tags=['hiking'])])
    msg = 'Which is the cheapest for a weekend hike?'
    d = ok(compose_text('Sounds like you are watching the budget.', 'Which of these do you need?', three, msg), cs=three, message=msg)
    assert 'For "hike":\n- Trail Backpack is tagged hiking.\n- Trail Socks is tagged hiking.\n- Steel Bottle has no matching tag (its tags: hydration).' in d.text
    assert 'Price: $59.00' in d.text and 'Price: $18.00' in d.text and 'Price: $12.00' in d.text  # the price answer line names only two of three, so no price may vanish
    same = enrich_cards([r(id=1, name='Day Pack', price=Decimal('45.00'), attributes={'weight': '1.2 kg'}, tags=['hiking']), r(id=2, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, tags=['hiking'])])
    msg = 'Which is lighter for hiking?'
    d = ok(compose_text('Both are packs.', 'What matters more to you?', same, msg), cs=same, message=msg)
    assert 'For "hiking":\n- Day Pack is tagged hiking.\n- Trail Backpack is tagged hiking.' in d.text


def test_compose_says_when_cards_tie_on_the_asked_criterion():
    """Offline stress (SIMULATED, SYNTHETIC cards): two cards tied on the asked price, rating or weight printed no answer line and said nothing about the tie. Code now states the tie from the listed values."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    r = lambda **k: catalog_result(row(**k))
    cs = enrich_cards([r(id=1, name='Pack A', price=Decimal('45.00'), attributes={'weight': '1 kg'}, tags=['hiking'], rating=4.5), r(id=2, name='Pack B', price=Decimal('45.00'), attributes={'weight': '1 kg'}, tags=['hiking'], rating=4.5)])
    msg = 'Which is cheapest and lightest?'
    d = ok(compose_text('Both are close.', 'What matters more?', cs, msg), cs=cs, message=msg)
    assert 'On price, Pack A and Pack B are tied at $45.00.' in d.text
    assert 'On weight, Pack A and Pack B are tied at 1 kg.' in d.text
    msg = 'Which is best rated?'
    d = ok(compose_text('Both are close.', 'What matters more?', cs, msg), cs=cs, message=msg)
    assert 'On rating, Pack A and Pack B are tied at 4.5 out of 5.' in d.text
    three = enrich_cards([r(id=1, name='Pack A', price=Decimal('45.00')), r(id=2, name='Pack B', price=Decimal('45.00')), r(id=3, name='Pack C', price=Decimal('50.00'))])
    d = ok(compose_text('Okay.', 'What matters more?', three, 'Which is cheapest?'), cs=three, message='Which is cheapest?')
    assert 'On price, Pack A and Pack B are tied at $45.00; next is Pack C at $50.00.' in d.text


def test_compose_states_which_cards_fit_a_budget_the_customer_typed():
    """A customer budget ("under $50") is a hard constraint. Code compares it to the listed prices and says which cards fit; the customer's own number is not repeated (it never enters the text), so no digit is typed outside a slot."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    r = lambda **k: catalog_result(row(**k))
    cs = enrich_cards([r(id=1, name='Day Pack', price=Decimal('45.00'), attributes={'weight': '1.2 kg'}), r(id=2, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}), r(id=3, name='Mini Pack', price=Decimal('30.00'), attributes={'weight': '400 g'})])
    msg = 'I need a pack under $50 for hiking'
    d = ok(compose_text('Let me narrow it down.', 'What matters more to you?', cs, msg), cs=cs, message=msg)
    assert 'Within your budget: Mini Pack at $30.00 and Day Pack at $45.00. Trail Backpack at $59.00 is over it.' in d.text
    msg = 'anything below 20 dollars?'
    d = ok(compose_text('Let me check.', 'What matters more to you?', cs, msg), cs=cs, message=msg)
    assert 'None of these is within your budget; the lowest listed is Mini Pack at $30.00.' in d.text
    for msg in ('I want a pack for hiking', 'a pack for up to 3 people'):
        d = ok(compose_text('Okay.', 'What matters more to you?', cs, msg), cs=cs, message=msg)
        assert 'budget' not in d.text
def test_compose_opening_cannot_claim_suitability_or_generalise():
    """Real run 24 (7:51 PM, published and review-approved): the model opening said "Both the backpack and the bottle work for a weekend hike, and the bottle generally comes out cheaper", while the code's own tag line says the bottle has no hiking tag. Suitability and generalising claims are not card facts, so compose rejects them in the model's two pieces."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    pack = catalog_result(row(id=2, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, tags=['hiking']))
    bottle = catalog_result(row(id=5, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}, tags=['hydration']))
    cs = enrich_cards([pack, bottle])
    for bad in ('Both work for a weekend hike.', 'Both [[name:2]] and [[name:5]] are good for a trek.', 'The bottle generally comes out cheaper.', 'Either one would suit you.', 'This one is handy for trips.', 'It usually costs less.'):
        with pytest.raises(SlotError):
            compose_text(bad, 'Which do you need?', cs, 'Which is the cheapest for a weekend hike?')
    with pytest.raises(SlotError):
        compose_text('Okay.', 'Which one fits you better?', cs, 'Which is the cheapest for a weekend hike?')
    ok(compose_text('You want the lowest price for a hike.', 'Which do you need?', cs, 'Which is the cheapest for a weekend hike?'), cs=cs, message='Which is the cheapest for a weekend hike?')


def test_compose_rejects_praise_words_that_slipped_the_suitability_list():
    """Real run 26 (9:51 PM, published and review-approved): the opening said "Both are solid picks for the trail." That is praise plus a suitability claim the cards do not support, and it passed the PR349 word list. Praise adjectives and "pick/choice" wording are rejected in the model pieces."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    pack = catalog_result(row(id=2, name='Trail Backpack', price=Decimal('59.00'), attributes={'weight': '650 g'}, tags=['hiking']))
    bottle = catalog_result(row(id=5, name='Steel Bottle', price=Decimal('18.00'), attributes={'capacity': '750 ml'}, tags=['hydration']))
    cs = enrich_cards([pack, bottle])
    for bad in ('Both are solid picks for the trail.', 'Two reliable options here.', 'Both are strong choices.', 'An excellent pair.', 'Nice combo, both sturdy.', 'Both are popular with hikers.', 'Great gear.', 'Both are well made.'):
        with pytest.raises(SlotError):
            compose_text(bad, 'Which do you need?', cs, 'Which is the cheapest for a weekend hike?')
    with pytest.raises(SlotError):
        compose_text('Okay.', 'Which is the smart pick for you?', cs, 'Which is the cheapest for a weekend hike?')
    ok(compose_text('You want the lowest spend for a trek.', 'Is price the main thing for this hike?', cs, 'Which is the cheapest for a weekend hike?'), cs=cs, message='Which is the cheapest for a weekend hike?')


def test_compose_says_when_the_customer_asked_about_something_no_card_lists():
    """Broad offline stress (88 SYNTHETIC questions, scripted writer, 10:58 PM): "Is the rain jacket waterproof and does it come in red?" and "does it work with android and is it waterproof?" got the card block and a question, with no word on the two things asked. Code now says plainly that the entries do not mention them, from a lexicon of common asks, and only when no card text covers the ask. Offline, not a model run."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    jacket = catalog_result(row(id=1, name='Rain Jacket', price=Decimal('89.00'), attributes={'material': 'nylon'}, description='Hooded jacket with taped seams.', tags=['jacket', 'rain']))
    cs = enrich_cards([jacket])
    msg = 'Is the rain jacket waterproof and does it come in red?'
    d = ok(compose_text('You want to know about the jacket.', 'What matters most to you?', cs, msg), cs=cs, message=msg)
    assert any(f in d.text for f in ("The entry for Rain Jacket doesn't mention waterproofing or colour options.", "The entry for Rain Jacket says nothing about waterproofing or colour options.", "Nothing in the catalog entry for Rain Jacket covers waterproofing or colour options."))
    assert 'each one' not in d.text and 'Here is what the catalog lists:' in d.text
    covered = catalog_result(row(id=1, name='Rain Jacket', price=Decimal('89.00'), attributes={'material': 'nylon'}, description='Fully waterproof hooded jacket.', tags=['jacket']))
    cs2 = enrich_cards([covered])
    d = ok(compose_text('You want to know about the jacket.', 'What matters most to you?', cs2, msg), cs=cs2, message=msg)
    assert 'waterproofing' not in d.text and 'colour options' in d.text
    quiet = ok(compose_text('You want to know about the jacket.', 'What matters most to you?', cs, 'Tell me about this jacket'), cs=cs, message='Tell me about this jacket')
    assert 'waterproofing' not in quiet.text and 'colour options' not in quiet.text
    pair = enrich_cards([catalog_result(row(id=1, name='Smart Watch', price=Decimal('150.00'), attributes={'battery': '2 days'})), catalog_result(row(id=2, name='Fitness Band', price=Decimal('45.00'), attributes={'weight': '25 g'}))])
    msg = 'does either work with android?'
    d = ok(compose_text('Let me check both.', 'What matters most to you?', pair, msg), cs=pair, message=msg)
    assert any(f in d.text for f in ('None of these entries mention compatibility details.', 'Nothing in these entries covers compatibility details.', 'These entries say nothing about compatibility details.'))


def test_compose_no_matching_tag_line_survives_a_card_whose_name_repeats_its_own_tag():
    """Broad offline stress (b035, "Need a shirt for a summer wedding"): Cotton Shirt (material cotton, tags shirt, casual, cotton) made the "no matching tag (its tags: ...)" line carry "cotton" twice once the name rendered, so render_slots raised slot_duplicate_value and the whole compose reply fell back. Same class as the shared-tag crash fixed in #346. The tags are already in the card block, so the line drops the parenthetical in that case."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    cotton = catalog_result(row(id=13, name='Cotton Shirt', price=Decimal('24.00'), attributes={'material': 'cotton'}, tags=['shirt', 'casual', 'cotton']))
    linen = catalog_result(row(id=14, name='Linen Shirt', price=Decimal('38.00'), attributes={'material': 'linen'}, tags=['shirt', 'summer', 'linen']))
    cs = enrich_cards([cotton, linen])
    msg = 'Need a shirt for a summer wedding'
    d = ok(compose_text('You are dressing for a wedding.', 'What matters most to you?', cs, msg), cs=cs, message=msg)
    assert 'Cotton Shirt has no matching tag.' in d.text


def test_compose_question_may_repeat_a_field_the_customer_named_even_when_no_card_lists_it():
    """Real Groq n=1 (11:03 PM, broad set b038, "Is the rain jacket waterproof and does it come in red?"): the model wrote the question "Which matters more to you, the waterproof feature or the red color?". compose_unlisted_field rejected it because no card lists a color, the compose reply fell back to the normal writer, and that draft was rejected for an unsupported stock claim (a deterministic validation failure, not a quota or reviewer failure). The customer used the word "color" first, so restating it is not an offer of a field the cards lack."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    jacket = catalog_result(row(id=19, name='Rain Jacket', price=Decimal('89.00'), attributes={'material': 'nylon'}, description='Hooded jacket with taped seams.', tags=['jacket']))
    cs = enrich_cards([jacket])
    msg = 'Is the rain jacket waterproof and does it come in red? Any color?'
    d = ok(compose_text('Sounds like you want to know if [[name:19]] is waterproof and if it comes in red.', 'Which matters more to you, the waterproof feature or the color?', cs, msg), cs=cs, message=msg)
    assert 'waterproofing or colour options' in d.text
    with pytest.raises(SlotError):
        compose_text('Here is the jacket.', 'Which weight do you prefer?', cs, 'Is it waterproof?')


def test_compose_flags_different_kinds_by_category_when_spec_keys_overlap():
    """Broad offline stress (88 SYNTHETIC questions): Studio Headphones (Headphones) vs Smart Watch (Wearables), and Laptop Sleeve vs Scented Candle style pairs, share a spec key such as connectivity or material, so the spec-key test never said they are different kinds and the reply still ended on the generic question. When two cards sit in different catalog categories the reply now says so, using the categories as listed."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    a = catalog_result(row(id=1, name='Studio Headphones', price=Decimal('79.00'), category='Headphones', attributes={'connectivity': 'Bluetooth'}))
    b = catalog_result(row(id=2, name='Smart Watch', price=Decimal('150.00'), category='Wearables', attributes={'connectivity': 'Bluetooth'}))
    cs = enrich_cards([a, b])
    msg = 'Compare these for someone who commutes by train'
    d = ok(compose_text('You are comparing two things for the train.', 'What matters most to you?', cs, msg), cs=cs, message=msg)
    assert kind_in(d.text, 'Studio Headphones is listed under Headphones and Smart Watch under Wearables, ')
    assert closer_in(d.text, 'Studio Headphones', 'Smart Watch')
    same = enrich_cards([catalog_result(row(id=1, name='Studio Headphones', price=Decimal('79.00'), category='Headphones', attributes={'connectivity': 'Bluetooth'})), catalog_result(row(id=3, name='Earbuds Mini', price=Decimal('49.00'), category='Headphones', attributes={'connectivity': 'Bluetooth'}))])
    d = ok(compose_text('You are comparing two things for the train.', 'What matters most to you?', same, msg), cs=same, message=msg)
    assert 'different kinds' not in d.text
    plain = enrich_cards([catalog_result(row(id=1, name='A Thing', price=Decimal('5.00'), attributes={'x': 'y'})), catalog_result(row(id=2, name='B Thing', price=Decimal('6.00'), attributes={'x': 'z'}))])
    d = ok(compose_text('Two things.', 'What matters most to you?', plain, msg), cs=plain, message=msg)
    assert 'different kinds' not in d.text


def test_two_names_that_share_a_material_word_do_not_trip_the_duplicate_value_check():
    """Broad offline stress (b039, b067): Wool Scarf and Wool Sweater both list material wool, so any one line naming both ("... which one are you actually after: Wool Scarf or Wool Sweater?") showed the value "wool" twice and render_slots raised slot_duplicate_value, throwing away the whole compose reply. Product names are the cards' own names, not typed facts, so they no longer count toward the duplicate check. A typed value outside the names still does."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    scarf = catalog_result(row(id=15, name='Wool Scarf', price=Decimal('30.00'), category='Accessories', attributes={'material': 'wool'}))
    sweater = catalog_result(row(id=20, name='Wool Sweater', price=Decimal('70.00'), category='Outerwear', attributes={'material': 'wool'}))
    cs = enrich_cards([scarf, sweater])
    msg = 'what about the second one?'
    d = ok(compose_text('You are looking at two warm things.', 'What matters most to you?', cs, msg), cs=cs, message=msg)
    assert closer_in(d.text, 'Wool Scarf', 'Wool Sweater')
    with pytest.raises(SlotError):
        render_slots({'text': 'It is wool, really wool.'}, cs, None, msg)


def test_compose_fixed_sentences_have_variants_and_all_of_them_validate():
    """Broad offline stress: across 88 questions the code-built "different kinds" sentence and the closing "These do different jobs, so which one are you actually after" were one fixed string each, and the not-listed line had one form. Real customers see the same canned sentence over and over. Each now has three variants picked from the customer's own message (so a given message always gets the same reply). The first variant is the old text; every variant must still pass the validator."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    a = catalog_result(row(id=1, name='Studio Headphones', price=Decimal('79.00'), category='Headphones', attributes={'connectivity': 'Bluetooth'}))
    b = catalog_result(row(id=2, name='Smart Watch', price=Decimal('150.00'), category='Wearables', attributes={'connectivity': 'Bluetooth'}))
    cs = enrich_cards([a, b])
    kinds, closers = set(), set()
    for i in range(30):
        msg = f'Compare these for someone who commutes by train, case {"x" * i}'
        d = ok(compose_text('You are comparing two things.', 'What matters most?', cs, msg), cs=cs, message=msg)
        paras = d.text.split('\n\n')
        kinds.add(next(p for p in paras if 'different kinds' in p or 'not substitutes' in p or 'not interchangeable' in p or 'not really alternatives' in p))
        closers.add(paras[-1])
    assert len(kinds) == 3 and len(closers) == 3
    jacket = enrich_cards([catalog_result(row(id=1, name='Rain Jacket', price=Decimal('89.00'), attributes={'material': 'nylon'}))])
    forms = set()
    for i in range(30):
        msg = f'Is it waterproof, case {"x" * i}?'
        d = ok(compose_text('You are asking about the jacket.', 'What matters most?', jacket, msg), cs=jacket, message=msg)
        forms.add(next(p for p in d.text.split('\n\n') if 'waterproofing' in p))
    assert len(forms) == 3


def test_compose_budget_line_understands_bucks_and_i_have_phrasing():
    """Broad offline stress (b021 "under 20 bucks for a coworker", b022 "I have 100 dollars. Can I buy two of these?", b019 "I can spend 50 dollars max"): the budget line only fired for "under/below/max ... $N" phrasing with a currency word from a short list, so "bucks" and "I have 100 dollars" / "my budget is 200 dollars" got no budget answer at all. Customers state budgets many ways; the line now also fires for "bucks", "I have N dollars", "budget is N", "spend N" and "limit N", still only with a currency word, still from listed prices."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    r = lambda **k: catalog_result(row(**k))
    cs = enrich_cards([r(id=1, name='Wool Scarf', price=Decimal('30.00'), attributes={'material': 'wool'}), r(id=2, name='Scented Candle', price=Decimal('16.00'), attributes={'burn time': '40 hours'}), r(id=3, name='Notebook A5', price=Decimal('9.00'), attributes={'pages': '160'})])
    for msg, fit in (('under 20 bucks for a coworker', 'Within your budget: Notebook A5 at $9.00 and Scented Candle at $16.00. Wool Scarf at $30.00 is over it.'),
                     ('I have 20 dollars', 'Within your budget: Notebook A5 at $9.00 and Scented Candle at $16.00. Wool Scarf at $30.00 is over it.'),
                     ('my budget is 20 dollars', 'Within your budget: Notebook A5 at $9.00 and Scented Candle at $16.00. Wool Scarf at $30.00 is over it.'),
                     ('I can spend 20 dollars on a gift', 'Within your budget: Notebook A5 at $9.00 and Scented Candle at $16.00. Wool Scarf at $30.00 is over it.')):
        d = ok(compose_text('A gift for work.', 'What matters most to you?', cs, msg), cs=cs, message=msg)
        assert fit in d.text, msg
    for quiet in ('I have 3 dogs', 'I need 2 of these', 'my budget is tight'):
        d = ok(compose_text('A gift for work.', 'What matters most to you?', cs, quiet), cs=cs, message=quiet)
        assert 'budget' not in d.text, quiet


def test_rejected_model_wording_falls_back_to_code_built_neutral_text_not_the_free_writer():
    """Real run b052 (Groq, home, one card, 'Can I use it on induction?'): the model's opening claimed induction use, compose rejected it, the free writer then published 'confirmed by the material spec' and the reviewer approved. The card says only material: cast iron. Code must publish its own reply instead."""
    from app.services.conversation.slot_copy import enrich_cards, compose_text
    from app.services.conversation.compose_copy import compose_text_safe
    pan = catalog_result(row(id=28, name='Cast Iron Pan', price=Decimal('48.00'), attributes={'material': 'cast iron'}, description='Pre-seasoned pan for the stove and the oven.'))
    cs = enrich_cards([pan])
    msg = 'Can I use it on induction?'
    bad_open, bad_q = 'Sure thing, the [[name:28]] works on induction stovetops.', 'Besides induction, are price or any other factor most important for you?'
    with pytest.raises(SlotError):
        compose_text(bad_open, bad_q, cs, msg)
    text = compose_text_safe(bad_open, bad_q, cs, msg)
    assert 'works on induction' not in text and 'Besides induction' not in text
    assert 'says nothing about induction' in text
    ok(text, cs=cs, message=msg)
    assert compose_text_safe('Let us take this one piece at a time.', 'What matters most to you here?', cs, msg) == compose_text('Let us take this one piece at a time.', 'What matters most to you here?', cs, msg)


def test_opening_may_not_answer_an_ask_the_cards_do_not_cover():
    """Real run b054 (Groq, beauty, one card, 'Is it ok for sensitive skin?'): the model opening said 'formulated to be gentle, so it should be fine for sensitive skin'. The card has no skin details. Only the reviewer stopped it (reviewer-only rejection); the code checks passed it."""
    from app.services.conversation.slot_copy import enrich_cards
    from app.services.conversation.compose_copy import compose_text, compose_text_safe
    cream = catalog_result(row(id=32, name='Face Moisturiser', price=Decimal('21.00'), attributes={'volume': '50 ml'}, description='Daily face cream.'))
    cs = enrich_cards([cream])
    msg = 'Is it ok for sensitive skin?'
    bad = 'I would say [[name:32]] is formulated to be gentle, so it should be fine for sensitive skin.'
    with pytest.raises(SlotError):
        compose_text(bad, 'Do you have any other skin concerns?', cs, msg)
    text = compose_text_safe(bad, 'Do you have any other skin concerns?', cs, msg)
    assert 'formulated' not in text and 'should be fine' not in text
    assert "doesn't mention skin or allergy" in text
    ok(text, cs=cs, message=msg)
    other = compose_text('Let us take this one piece at a time.', 'What else should I check for you?', cs, 'What is in the box?')
    assert other
    # a card that does list the topic may be echoed
    both = enrich_cards([catalog_result(row(id=33, name='Calm Cream', price=Decimal('21.00'), attributes={'skin': 'sensitive skin tested'}))])
    assert compose_text('Sensitive skin, got it.', 'Anything else?', both, msg)


def test_quantity_total_is_computed_by_code_and_passes_the_number_check():
    """Open gap from the broad set: "4 of these" got no total because the model may not type numbers. Code now reads the quantity from the customer's message, multiplies the card price in Decimal and renders it through a validated slot."""
    from app.services.conversation.slot_copy import enrich_cards
    from app.services.conversation.compose_copy import compose_text
    from app.services.conversation.compose_facts import quantity_of
    assert [quantity_of(m) for m in ('I need 4 of these', 'can I get three of them', 'what is the price for 12 pieces', 'buy 2', 'x5 please', 'I have 4 kids', 'is it 3 hours?', 'a dozen of these', 'one of them')] == [4, 3, 12, 2, 5, None, None, 12, None]
    cs = enrich_cards(cards())
    msg = 'How much for 4 of the Studio Headphones?'
    text = compose_text('You want a straight answer, so here it is.', 'What else should I check for you?', cs[:1], msg)
    d = ok(text, cs=cs[:1], message=msg)
    assert '4 x $79.00 = $316.00' in d.text
    two = ok(compose_text('You want a straight answer, so here it is.', 'What else should I check for you?', cs, msg), cs=cs, message=msg)
    assert '4 x $79.00 = $316.00' in two.text and '4 x $18.00 = $72.00' in two.text
    none = compose_text('You want a straight answer, so here it is.', 'What else should I check for you?', cs[:1], 'How much is it?')
    assert ' x ' not in none


def test_quantity_changes_the_budget_check_to_the_whole_order():
    """Offline b022: 'I have 100 dollars. Can I buy two of these?' said 'Within your budget' for single prices while two units cost more."""
    from app.services.conversation.slot_copy import enrich_cards
    from app.services.conversation.compose_copy import compose_text
    cs = enrich_cards(cards())
    msg = 'I have 50 dollars. Can I buy two of these?'
    d = ok(compose_text('You want a straight answer, so here it is.', 'What else should I check for you?', cs, msg), cs=cs, message=msg)
    assert 'At your quantity, Steel Bottle stays within your budget and Studio Headphones goes over it.' in d.text
    assert 'Within your budget:' not in d.text
