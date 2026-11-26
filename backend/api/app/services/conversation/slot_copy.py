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
    "[[name:ID]] for a product name, [[price:ID]] for its price, [[spec.KEY:ID]] for a listed spec value, [[total]] and [[left]] for the combined price and the budget left when they are provided. "
    "Use only IDs and spec keys that appear in the supplied cards. A fact with no slot is unknown: say plainly that you do not have it, in your own words, without slots. "
    "Everything else is free: write like a sharp, tactful friend, vary the shape and length to the customer's intent, use short bullet lines only for two or more precise facts."
)


class SlotDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: StrictStr = Field(min_length=1, max_length=2000)


class SlotError(ValueError):
    """A slot the cards cannot back, or a fact typed outside a slot."""


def _money(card):
    try:
        amount = Decimal(str(card['price'])).quantize(Decimal('0.01'))
    except (InvalidOperation, KeyError, TypeError):
        raise SlotError('slot_price_unavailable')
    cur = card.get('currency')
    if not cur:
        raise SlotError('slot_price_unavailable')
    return (_SYMBOL[cur] + str(amount)) if cur in _SYMBOL else f'{amount} {cur}', str(amount)


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
        if key == 'stock':
            if not re.search(r'stock|availab|in store|pick ?up', message or '', re.I):
                raise SlotError('slot_stock_not_asked')
            words = _STOCK_WORDS.get(card.get('stock_status'))
            if not words:
                raise SlotError('slot_stock_unavailable')
            claim(pid, 'stock_status', card['stock_status'])
            return words
        raise SlotError('slot_unknown_kind')

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
    rendered = _SLOT.sub(fill, text)
    return ShoppingDraft(text=rendered, product_ids=ids, claims=claims)
