"""Slot copy: the model writes the voice, code writes every fact.

Root cause this addresses: a single free-text call writes facts and voice together, and code can only scan words for facts, so each model
habit (IDs, jargon, mismatched numbers) needed another phrase rule. Here the model writes prose with fact slots such as [[name:2]],
[[price:2]], [[spec.weight:2]], [[total]] and [[left]]. Code renders each slot from the card, builds product_ids and claims from the slots
itself, and rejects literal digits or links outside slots. The result is an ordinary ShoppingDraft, so the existing validator and review
run on it unchanged. Not wired into live traffic. Soft judgments ("a fair size") and number words are NOT covered and still need review.
"""
import json
import re
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from app.services.conversation.shopping_copy import Claim, ShoppingDraft, exact_totals

_SLOT = re.compile(r"\[\[\s*([a-z_.]+?)(?::\s*(\d+))?\s*\]\]")
_ANY_BRACKETS = re.compile(r"\[\[|\]\]")
_NUMBER_WORD_FACT = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|hundred|thousand|dozen|half|double|triple)"
    r"(?:[- ](?:and a half|hundred|thousand|a|an))?[- ]+(?:hours?|days?|weeks?|minutes?|years?|months?|grams?|kilograms?|kilos?|liters?|litres?|ml|cm|mm|inches|inch|pounds?|dollars?|euros?|percent|per cent|watts?|gb|mah|stars?|reviews?)\b", re.I)
_SYMBOL = {'USD': '$', 'EUR': '€', 'GBP': '£'}
_STOCK_WORDS = {'local_in_stock': 'in stock', 'fixture_in_stock': 'in stock', 'local_out_of_stock': 'out of stock', 'fixture_out_of_stock': 'out of stock'}

SLOT_WRITER_RULES = (
    "Write the reply as JSON {text}. Never type a number, price, measurement, product ID or link yourself. Every fact comes from a slot that the shop fills in: "
    "[[name:ID]] for a product name, [[price:ID]] for its price, [[spec.KEY:ID]] for a listed spec value, [[no_promise]] for the refusal to promise stock or delivery, [[total]] and [[left]] for the combined price and the budget left when they are provided. "
    "[[card:ID]] prints one product's name, price and every listed fact (specs, rating, tags, description) exactly: when you compare products, put one [[card:ID]] on its own line starting with \"- \" for each, and do not restate any of those facts anywhere else. Use only IDs and spec keys that appear in the supplied cards. A fact with no slot is unknown: say plainly that you do not have it, in your own words, without slots. "
    "Voice: you are a warm, sharp human sales engineer talking to one person, not a catalog and not a form. Length follows the data: 120 to 220 words in three or four short paragraphs when the cards carry several slot facts per product, but only 60 to 110 words in two short paragraphs when a product has one or two slot facts, and never restate a missing fact twice. Plus a short bullet block (lines starting with \"- \") only when you compare two or more products. Answer their actual question first and take a position the slot facts support (for example, start with one product and say which slot fact is the reason). Then walk through their situation (their trip, desk, budget, routine): connect each slot fact to what it means for them in plain words, name a real trade-off between the options, and say what you cannot see, listing the specific missing facts. Talk like a person: contractions, varied sentence length, a light touch of wit, speak to \"you\". Consequences and trade-offs must follow from slot facts only, and never add a fact, number or feature, and never use general knowledge about product types (for example, that a lighter pack means less strain). Finish with one specific question that moves the decision forward. Do not guess what a value implies (a number being the only one listed does not make a product light, strong or good); state the slot value and let the customer weigh it. Every bullet must carry at least one slot value; never write a bullet that only says a product has a spec. "
    "A card may list description, tags and rating among its catalog_specs: these are the source\'s own words and numbers. Use them only through [[spec.description:ID]], [[spec.tags:ID]] and [[spec.rating:ID]], and add no meaning to them. Never restate a description in your own words: any feature, size, number or material from it appears only through its slot, and a feature the description does not state is unknown. Do not call ratings solid, strong or great; show the rating slot as it is. "
    "Stay consistent: never say you lack details on a product and then state facts about it; name the specific thing you lack instead (for example, no volume or battery figure). When the customer asks what you do not know, list those specific missing things. Use no adjective that a slot fact does not show (lightweight, durable, sturdy, compact, premium). "
    "Do not rank or praise a product (better, best, ideal, lightweight, perfect, great) unless a slot fact shows it: the review rejects judgments no card supports. When asked which is better, say what each one does with its slot facts and ask what matters most to the customer. "
    "When the customer asks about delivery, shipping, guarantees, returns or merchant stock, write the slot [[no_promise]] (the shop fills in a plain refusal) and do not mention shipping, delivery, next-day or guarantees anywhere else, and never offer items with confirmed delivery. "
    "Never mention warranty, returns, shipping, delivery or guarantees (not even to say you do not know) unless the customer asked about them. Never open with a stock phrase (Here's a rundown, Sure thing, Great question), no exclamation marks, no greeting. Vary the shape and wording from reply to reply; do not reuse a fixed template. Everything else is free."
)


class SlotDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: StrictStr = Field(min_length=1, max_length=2000)


from app.services.conversation.slot_errors import SlotError  # noqa: F401 (re-exported)

def _money(card):
    try:
        amount = Decimal(str(card['price'])).quantize(Decimal('0.01'))
    except (InvalidOperation, KeyError, TypeError):
        raise SlotError('slot_price_unavailable')
    cur = card.get('currency')
    if not cur:
        raise SlotError('slot_price_unavailable')
    return (_SYMBOL[cur] + str(amount)) if cur in _SYMBOL else f'{amount} {cur}', str(amount)


_TAIL = re.compile(r"\s*\[\[name:(\d+)\]\]\s*\[\[spec\.([a-z_.]+?):(\d+)\]\]\s*$")


def _drop_citation_tails(text, by_id):
    """A line that types a card value and then ends with "[[name:P]] [[spec.K:P]]" cites a value it already wrote: drop the tail so the value shows once."""
    out = []
    for line in text.split('\n'):
        m = _TAIL.search(line)
        card = by_id.get(int(m.group(3))) if m and m.group(1) == m.group(3) else None
        if card is not None:
            value = str((card.get('catalog_specs') or {}).get(m.group(2)) or '').strip()
            head = line[:m.start()]
            if value and re.search(r'(?<![\w])' + r'\s+'.join(re.escape(w) for w in value.split()) + r'(?![\w])', _SLOT.sub(' ', head), re.I):
                line = head
        out.append(line)
    return '\n'.join(out)


def _drop_typed_echoes(text, by_id):
    """A value typed directly before its own spec slot ("650 g [[spec.weight:2]]") is a redundant echo of the card value: drop it. Any other typed value stays and is rejected later."""
    for m in reversed(list(_SLOT.finditer(text))):
        key, pid_text = m.group(1), m.group(2)
        card = by_id.get(int(pid_text)) if pid_text else None
        if not key.startswith('spec.') or card is None:
            continue
        value = str((card.get('catalog_specs') or {}).get(key[5:]) or '').strip()
        if not value:
            continue
        head = text[:m.start()]
        tail = re.search(r'(?:^|(?<=\s))' + r'\s+'.join(re.escape(w) for w in value.split()) + r'\s*$', head, re.I)
        if tail:
            text = head[:tail.start()] + text[m.start():]
    return text


def _typed_values_to_slots(text, by_id):
    """A card spec value typed in a line that is about exactly one product (named in plain words or by slot) is that product's own fact: render it from the slot. Lines about several products, or values not on the card, stay typed and are rejected later."""
    out = []
    for line in text.split('\n'):
        pids = {int(m.group(2)) for m in _SLOT.finditer(line) if m.group(2)}
        low = _SLOT.sub(' ', line).casefold()
        pids |= {pid for pid, card in by_id.items() if str(card['name']).casefold() in low}
        if len(pids) == 1 and next(iter(pids)) in by_id:
            pid = next(iter(pids))
            for key, value in sorted(((by_id[pid].get('catalog_specs') or {}).items()), key=lambda kv: -len(str(kv[1]))):
                value = str(value).strip()
                if not value:
                    continue
                pat = re.compile(r'(?<![\w])' + r'\s+'.join(re.escape(w) for w in value.split()) + r'(?![\w])', re.I)
                parts, last = [], 0
                for m in _SLOT.finditer(line):
                    parts.append(pat.sub('[[spec.%s:%d]]' % (key, pid), line[last:m.start()], count=1)); parts.append(m.group(0)); last = m.end()
                parts.append(pat.sub('[[spec.%s:%d]]' % (key, pid), line[last:], count=1))
                line = ''.join(parts)
        out.append(line)
    return '\n'.join(out)


def enrich_cards(cards):
    """Slot path only: copies of the cards whose catalog_specs also carry the source description, tags and rating, so they are exact slot facts. An attribute with the same key wins."""
    out = []
    for card in cards:
        extra = {}
        if card.source_description:
            extra['description'] = card.source_description
        if card.source_tags:
            extra['tags'] = ', '.join(card.source_tags)
        if card.source_rating:
            extra['rating'] = card.source_rating
        extra = {k: v for k, v in extra.items() if k not in card.catalog_specs}
        out.append(card.model_copy(update={'catalog_specs': {**card.catalog_specs, **extra}}) if extra else card)
    return out


def _check_fact_owner(text, by_id):
    """In one sentence, a price or spec slot must belong to the product named most recently before it (slot or plain name). A fact under another product's name is a wrong attribution."""
    names = {pid: str(card['name']).casefold() for pid, card in by_id.items()}
    for sentence in re.split(r'(?<=[.!?])\s+|\n', text):
        refs = []
        for m in _SLOT.finditer(sentence):
            if m.group(1) == 'name' and m.group(2):
                refs.append((m.start(), int(m.group(2))))
        low = _SLOT.sub(lambda m: ' ' * len(m.group(0)), sentence).casefold()
        for pid, name in names.items():
            at = low.find(name)
            while at != -1:
                refs.append((at, pid))
                at = low.find(name, at + 1)
        refs.sort()
        for m in _SLOT.finditer(sentence):
            if (m.group(1) == 'price' or m.group(1).startswith('spec.')) and m.group(2):
                before = [pid for pos, pid in refs if pos < m.start()]
                if before and before[-1] != int(m.group(2)):
                    raise SlotError('slot_wrong_product')


def _typed_fact(sentence, own):
    outside = _SLOT.sub('\0', sentence)
    checked = re.sub(r'\b[A-Za-z]+\d+[A-Za-z0-9]*', lambda m: ' ' if m.group(0).casefold() in own else m.group(0), outside)
    return bool(re.search(r'\d', checked) or re.search(r'https?://|www\.', outside, re.I) or _NUMBER_WORD_FACT.search(outside))


def _drop_fact_sentences(text, message):
    """Drop the sentences that carry a typed number, link or number-word fact (only removes content, never adds). More than two dropped sentences means the draft is not usable."""
    own = {t.casefold() for t in re.findall(r'\b[A-Za-z]+\d+[A-Za-z0-9]*', message or '')}
    dropped, lines = 0, []
    for line in text.split('\n'):
        kept = []
        for sentence in re.split(r'(?<=[.!?])\s+', line):
            if sentence and _typed_fact(sentence, own):
                dropped += 1
            else:
                kept.append(sentence)
        lines.append(' '.join(kept))
    if dropped > 2:
        raise SlotError('slot_literal_fact')
    out = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
    return out if out else text


def render_slots(raw, cards, brief=None, message=None):
    """Return a ShoppingDraft whose text, product_ids and claims are built from slots, or raise SlotError."""
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else dict(raw)
    text = data.get('text')
    if not isinstance(text, str) or not text.strip() or set(data) - {'text'}:
        raise SlotError('slot_shape')
    by_id = {card.id: card.model_dump() for card in cards}
    totals = exact_totals(cards, brief)
    ids, claims = [], []

    def claim(pid, field, value):
        if pid not in ids:
            ids.append(pid)
            claims.append(Claim(product_id=pid, field='name', value=str(by_id[pid]['name'])))
        if field != 'name' and not any(c.product_id == pid and c.field == field for c in claims):
            claims.append(Claim(product_id=pid, field=field, value=value))

    def fill(match):
        key, pid_text = match.group(1), match.group(2)
        if key == 'no_promise':
            if pid_text:
                raise SlotError('slot_unknown_kind')
            return "I can't promise merchant stock or delivery timing."
        if key in ('total', 'left'):
            if pid_text or not totals:
                raise SlotError('slot_total_unavailable')
            if key == 'total':
                value = totals['combined_listed_price']
            else:
                value = totals.get('budget_remaining')
                if value is None:
                    raise SlotError('slot_total_unavailable')
            cur = totals['currency']
            return (_SYMBOL[cur] + value) if cur in _SYMBOL else f'{value} {cur}'
        if pid_text is None:
            raise SlotError('slot_product_missing')
        pid = int(pid_text)
        card = by_id.get(pid)
        if card is None:
            raise SlotError('slot_unknown_product')
        if key in ('card', 'cardnp'):
            specs = dict(card.get('catalog_specs') or {})
            shown, exact = _money(card)
            claim(pid, 'name', card['name'])
            claim(pid, 'price', exact)
            parts = [str(card['name'])] + ([f'  - Price: {shown}'] if key == 'card' else [])
            for k, v in specs.items():
                if k in ('description', 'rating', 'tags') or not str(v).strip():
                    continue
                claim(pid, 'spec.' + k, str(v))
                parts.append(f"  - {k.replace('_', ' ').capitalize()}: {v}")
            if specs.get('rating'):
                claim(pid, 'spec.rating', specs['rating'])
                parts.append(f"  - Rating: {specs['rating']}")
            if specs.get('tags'):
                claim(pid, 'spec.tags', specs['tags'])
                parts.append(f"  - Tags: {specs['tags']}")
            if specs.get('description'):
                claim(pid, 'spec.description', specs['description'])
                parts.append(f"  - Description: {str(specs['description']).strip()}")
            return '\n'.join(parts)
        if key == 'name':
            claim(pid, 'name', card['name'])
            return str(card['name'])
        if key == 'price':
            shown, exact = _money(card)
            claim(pid, 'price', exact)
            return shown
        if key.startswith('spec.'):
            value = (card.get('catalog_specs') or {}).get(key[5:])
            if value is None or str(value).strip() == '':
                raise SlotError('slot_spec_unavailable')
            claim(pid, key, str(value))
            return str(value)
        if key == 'qty':
            from app.services.conversation.compose_facts import quantity_of
            n = quantity_of(message)
            if not n:
                raise SlotError('slot_quantity_not_asked')
            shown, exact = _money(card)
            claim(pid, 'price', exact)
            total = (Decimal(exact) * n).quantize(Decimal('0.01'))
            cur = card.get('currency')
            return f"{n} x {shown} = " + ((_SYMBOL[cur] + str(total)) if cur in _SYMBOL else f'{total} {cur}')
        if key == 'stock':
            if not re.search(r'stock|availab|in store|pick ?up', message or '', re.I):
                raise SlotError('slot_stock_not_asked')
            words = _STOCK_WORDS.get(card.get('stock_status'))
            if not words:
                raise SlotError('slot_stock_unavailable')
            claim(pid, 'stock_status', card['stock_status'])
            return words
        raise SlotError('slot_unknown_kind')

    text = _typed_values_to_slots(_drop_typed_echoes(_drop_citation_tails(text, by_id), by_id), by_id)
    text = _drop_fact_sentences(text, message)
    outside = _SLOT.sub('\0', text)
    if _ANY_BRACKETS.search(outside) or '\0' in text:
        raise SlotError('slot_malformed')
    # Model-style words (letters first, then digits) that the customer typed themselves (PS5, USB3). Digit-first tokens such as 30h or 4K stay facts are echoes, not claimed facts.
    own = {t.casefold() for t in re.findall(r'\b[A-Za-z]+\d+[A-Za-z0-9]*', message or '')}
    checked = re.sub(r'\b[A-Za-z]+\d+[A-Za-z0-9]*', lambda m: ' ' if m.group(0).casefold() in own else m.group(0), outside)
    if re.search(r'\d', checked) or re.search(r'https?://|www\.', outside, re.I):
        raise SlotError('slot_literal_fact')
    if _NUMBER_WORD_FACT.search(outside):
        raise SlotError('slot_number_word_fact')
    _check_fact_owner(text, by_id)
    rendered = _SLOT.sub(fill, text)
    # A product named in plain words (no slot) is still the card's exact name: declare it, as the normal writer path does.
    low = rendered.casefold()
    for pid, card in by_id.items():
        if pid not in ids and str(card['name']).casefold() in low:
            ids.append(pid)
            claims.append(Claim(product_id=pid, field='name', value=str(card['name'])))
    names = sorted({str(c['name']) for c in by_id.values() if str(c.get('name', '')).strip()}, key=len, reverse=True)
    for line in rendered.split('\n'):
        for nm in names:
            line = re.sub(re.escape(nm), ' ', line, flags=re.I)  # a product name is the card's own name, not a typed fact
        for card in by_id.values():
            for value in (card.get('catalog_specs') or {}).values():
                value = str(value).strip()
                if value and len(re.findall(r'(?<![\w])' + re.escape(value) + r'(?![\w])', line, re.I)) > 1:
                    raise SlotError('slot_duplicate_value')
    return ShoppingDraft(text=rendered, product_ids=ids, claims=claims)


MASKED_RULES = (
    "Fact values are hidden from you on purpose: every price and spec shows as its own slot token (for example [[spec.weight:2]]). Write the token where the fact belongs and reason only about which facts exist and which are missing, never about how big, light or long a value is. "
)


def mask_payload(payload):
    """Optional slot mode (AIRDELIVER_SLOT_MASK=1): a copy of the writer payload whose card prices and spec values are replaced by their own slot tokens, so the model has no digits or description words to copy. Code still renders the values from the real cards."""
    out = dict(payload)
    cards = []
    for card in payload.get('catalog_evidence') or []:
        card = dict(card)
        pid = card.get('id')
        if card.get('price') is not None:
            card['price'] = f'[[price:{pid}]]'
        card['catalog_specs'] = {k: f'[[spec.{k}:{pid}]]' for k in (card.get('catalog_specs') or {})}
        cards.append(card)
    out['catalog_evidence'] = cards
    if 'exact_totals' in out:
        out['exact_totals'] = {'total': '[[total]]', 'budget_remaining': '[[left]]'}
    return out


# Compose mode lives in compose_copy.py, compose_facts.py and compose_asks.py; every old name stays importable from here.
from app.services.conversation.compose_facts import _listed, _label, _join, _card_words, _grams, _names, _need_lines  # noqa: E402,F401
from app.services.conversation.compose_asks import _UNLISTED_ASKS, _pick, _unlisted_lines, _tag_echoes_card  # noqa: E402,F401
from app.services.conversation.compose_copy import ComposeDraft, COMPOSE_RULES, compose_text, compose_text_safe  # noqa: E402,F401
