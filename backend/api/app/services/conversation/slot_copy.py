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
    for line in rendered.split('\n'):
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


class ComposeDraft(BaseModel):
    """Compose mode: the model writes only a short opening and one closing question."""
    model_config = ConfigDict(extra='forbid')
    opening: StrictStr = Field(min_length=1, max_length=300)
    question: StrictStr = Field(min_length=1, max_length=240)


COMPOSE_RULES = (
    "You write only two short pieces for a shopping reply; code adds every fact. opening: one or two sentences (at most 35 words) that answer the customer's situation in plain, warm words, like a sharp friend. question: one specific question (at most 25 words) about what matters most to the customer, only about topics the customer wrote or the listed fields (price, weight, rating, tags); never name a use or feature the customer did not mention. When the cards look like two different kinds of item, ask which of them the customer actually needs; never ask whether price is the only factor. "
    "Both pieces must contain no digits, no prices, no measurements, no product features, no praise or ranking (best, better, ideal, perfect, lightweight, great) and no promises about stock, delivery, warranty or returns. You may name a product only as [[name:ID]] with an ID from the supplied cards. Return JSON with keys opening and question only."
)


def _listed(card):
    keys = ['price'] if card.get('price') is not None else []
    keys += [k for k, v in (card.get('catalog_specs') or {}).items() if str(v).strip()]
    return keys


def _label(key):
    return key.replace('_', ' ')


def _join(items):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def _card_words(cs, tags=True):
    out = set()
    for c in cs:
        specs = c.get('catalog_specs') or {}
        for k in (('description', 'tags') if tags else ('description',)):
            out |= {w[:5] for w in re.findall(r'[a-z]{5,}', str(specs.get(k, '')).casefold())}
        for k, v in specs.items():
            if k not in ('description', 'tags', 'rating'):
                out |= {w[:5] for w in re.findall(r'[a-z]{5,}', str(v).casefold())}
    return out


def _grams(value):
    m = re.match(r'\s*(\d+(?:\.\d+)?)\s*(kg|g)\b', str(value), re.I)
    return Decimal(m.group(1)) * (1000 if m.group(2).lower() == 'kg' else 1) if m else None


def _names(ids):
    return ' and '.join(f'[[name:{i}]]' for i in ids)


def _need_lines(message, cs):
    """Facts that answer what the customer asked for (lowest price, highest rating, lowest weight), from listed values only, through slots, only when asked."""
    low = (message or '').casefold()
    out = []
    def ranked(values, reverse):
        items = sorted(((v, c['id']) for c, v in values if v is not None), reverse=reverse)
        return items if len(items) >= 2 and items[0][0] != items[1][0] else []
    def tied(values, reverse):
        items = sorted(((v, c['id']) for c, v in values if v is not None), reverse=reverse)
        top = sorted(i for v, i in items if items and v == items[0][0])
        if len(items) >= 2 and len(top) >= 2:
            rest = [i for v, i in items if v != items[0][0]]
            return top, (rest[0] if rest else None)
        return None
    if re.search(r'cheap|budget|lowest price|afford|least expensive|inexpensive', low):
        vals = []
        for c in cs:
            try:
                vals.append((c, Decimal(str(c['price']))))
            except Exception:
                pass
        r = ranked(vals, False)
        tie = tied(vals, False) if not r else None
        if tie:
            top, nxt = tie
            out.append(f'On price, {_names(top)} are tied at [[price:{top[-1]}]]' + (f'; next is [[name:{nxt}]] at [[price:{nxt}]].' if nxt else '.'))
        if r:
            out.append(f'On price, [[name:{r[0][1]}]] is the lowest listed at [[price:{r[0][1]}]]; next is [[name:{r[1][1]}]] at [[price:{r[1][1]}]].')
    cap = re.search(r'(?:under|below|less than|max(?:imum)?|within|up to|at most|no more than)\s*(?:\$|usd|€|£)?\s*(\d+(?:[.,]\d+)?)|(?:\$|€|£)\s*(\d+(?:[.,]\d+)?)\s*(?:or less|max|tops)?', low)
    if cap and re.search(r'[$€£]|usd|dollars?|euros?|pounds?|budget', low) and re.search(r'under|below|less than|max|within|up to|at most|no more than|or less|tops', low):
        try:
            limit = Decimal((cap.group(1) or cap.group(2)).replace(',', '.'))
        except Exception:
            limit = None
        priced = []
        for c in cs:
            try:
                priced.append((Decimal(str(c['price'])), c['id']))
            except Exception:
                pass
        priced.sort()
        if limit is not None and len(priced) >= 2:
            fit = [i for v, i in priced if v <= limit]
            over = [i for v, i in priced if v > limit]
            if fit:
                text = 'Within your budget: ' + ' and '.join(f'[[name:{i}]] at [[price:{i}]]' for i in fit) + '.'
                if over:
                    text += ' ' + ' and '.join(f'[[name:{i}]] at [[price:{i}]]' for i in over) + (' is' if len(over) == 1 else ' are') + ' over it.'
                out.append(text)
            else:
                out.append(f'None of these is within your budget; the lowest listed is [[name:{priced[0][1]}]] at [[price:{priced[0][1]}]].')
    if re.search(r'rating|rated|reviews?\b|top.?rated', low):
        vals = []
        for c in cs:
            m = re.match(r'\s*(\d+(?:\.\d+)?)', str((c.get('catalog_specs') or {}).get('rating', '')))
            vals.append((c, Decimal(m.group(1)) if m else None))
        r = ranked(vals, True)
        tie = tied(vals, True) if not r else None
        if tie and not tie[1]:
            out.append(f'On rating, {_names(tie[0])} are tied at [[spec.rating:{tie[0][-1]}]].')
        if r:
            out.append(f'On rating, [[name:{r[0][1]}]] lists the highest: [[spec.rating:{r[0][1]}]]. [[name:{r[1][1]}]] lists [[spec.rating:{r[1][1]}]].')
    if re.search(r'light|weigh|heavy', low):
        wv = [(c, _grams((c.get('catalog_specs') or {}).get('weight'))) for c in cs]
        r = ranked(wv, False)
        tie = tied(wv, False) if not r else None
        if tie and not tie[1]:
            out.append(f'On weight, {_names(tie[0])} are tied at [[spec.weight:{tie[0][-1]}]].')
        if r:
            out.append(f'On weight, [[name:{r[0][1]}]] lists the lowest: [[spec.weight:{r[0][1]}]]. [[name:{r[1][1]}]] lists [[spec.weight:{r[1][1]}]].')
    return out


def compose_text(opening, question, cards, message=None):
    """Compose mode (AIRDELIVER_SLOT_COMPOSE=1): code builds everything between the model's opening and question from the cards alone: one fact block per product and what each card does not list. Only name slots and the card block carry values."""
    cs = [c.model_dump() if hasattr(c, 'model_dump') else dict(c) for c in cards]
    allowed = {w[:5] for w in re.findall(r'[a-z]{5,}', (message or '').casefold())}
    for c in cs:
        allowed |= {w[:5] for w in re.findall(r'[a-z]{5,}', str(c.get('name', '')).casefold())}
    strip = lambda t: re.sub(r'\[\[name:\d+\]\]', ' ', t).casefold()
    stripped = strip(f'{opening} {question}')
    if re.search(r'\b(?:free|deliver\w*|ship\w*|warrant\w*|guarant\w*|return\w*|refund\w*|reserv\w*|discount\w*|special offers?|promo\w*|coupon\w*|deals?|stock|available|availability)\b', stripped):
        raise SlotError('compose_policy_wording')
    if re.search(r'\b(?:work|works|working|worked|suit|suits|suited|suitable|fit|fits|fitting|good|ideal|perfect|great|handy|useful|right)\s+(?:for|well|you)\b|\b(?:would|could|will|can)\s+(?:suit|work|fit)\b|\b(?:generally|usually|typically|often|tends?|normally|mostly)\b|\bsuit\w*\b|\bfits?\b', stripped):
        raise SlotError('compose_suitability_claim')
    words = lambda t: {w[:5] for w in re.findall(r'[a-z]{5,}', t)}
    if words(strip(opening)) & (_card_words(cs) - allowed) or words(strip(question)) & (_card_words(cs, tags=False) - allowed):
        raise SlotError('compose_card_wording')
    listed = {c['id']: _listed(c) for c in cs}
    have = {_label(k) for ks in listed.values() for k in ks} | {'rating' for c in cs if (c.get('catalog_specs') or {}).get('rating')}
    for field in ('weight', 'capacity', 'rating', 'battery', 'material', 'size', 'color', 'colour', 'dimensions', 'warranty', 'price'):
        if re.search(r'\b' + field + r'\b', question.casefold()) and field not in have:
            raise SlotError('compose_unlisted_field')
    union = []
    for c in cs:
        union += [k for k in listed[c['id']] if k not in union]
    heading = ('What the catalog lists for each:', 'Here is what each one lists:', 'The listed details, side by side:')[sum(map(ord, message or '')) % 3]
    needs = _need_lines(message, cs)
    low = (message or '').casefold()
    cardkey = 'cardnp' if len(cs) <= 2 and any(n.startswith('On price') for n in needs) else 'card'  # the answer line names two prices only; with 3+ cards the blocks keep theirs
    parts = [opening.strip()] + ([' '.join(needs)] if needs else [])
    different = False
    keysets = [{k for k in listed[c['id']] if k not in ('price', 'description', 'rating', 'tags')} for c in cs]
    if len(cs) == 2 and all(keysets) and not (keysets[0] & keysets[1]):
        names = [f"[[name:{c['id']}]]" for c in cs]
        different = True
        parts.append(f"{names[0]} is listed with a {_join([_label(k) for k in sorted(keysets[0])])} and {names[1]} with a {_join([_label(k) for k in sorted(keysets[1])])}, so they look like two different kinds of item, not substitutes.")
    parts += [heading, '\n'.join(f"- [[{cardkey}:{c['id']}]]" for c in cs)]
    asked = lambda label: label in low or (label == 'weight' and re.search(r'light|weigh|heavy', low)) or (label == 'rating' and re.search(r'rated|review', low))
    gaps = []
    for c in cs:
        missing = [_label(k) for k in union if k not in listed[c['id']] and asked(_label(k))]
        if missing:
            gaps.append(f"[[name:{c['id']}]] has no separate {_join(missing)} entry.")
    if gaps and len(cs) >= 2:
        gaps.append('So the two cannot be compared directly on those points.' if len(cs) == 2 else 'So they cannot be compared directly on those points.')
        if any((c.get('catalog_specs') or {}).get('description') for c in cs):
            gaps.append('Check each description for anything beyond these entries.')
    if gaps:
        parts.append(' '.join(gaps))
    qwords = {w for w in re.findall(r'[a-z]{4,}', low)}
    fits = []
    for c in cs:
        tags = [x.strip() for x in str((c.get('catalog_specs') or {}).get('tags', '')).split(',') if len(x.strip()) >= 4]
        hit = None
        for tag in tags:
            word = next((w for w in sorted(qwords) if w[:3] == tag.casefold()[:3]), None)
            if word and tag.casefold() not in str(c.get('name', '')).casefold():
                hit = (tag, word)
                break
        fits.append((c, tags, hit))
    hits = [f for f in fits if f[2]]
    if hits:
        word = hits[0][2][1]
        others = [f for f in fits if not f[2] and f[1] and not any(g[:3] == word[:3] for g in (x.casefold() for x in f[1]))]
        if others or len(hits) > 1:
            seg = [f'- [[name:{c["id"]}]] is tagged {h[0]}.' for c, _, h in hits] + [f'- [[name:{c["id"]}]] has no matching tag (its tags: {", ".join(tags)}).' for c, tags, _ in others]
            parts.append(f'For "{word}":\n' + '\n'.join(seg))
        else:
            parts.append(' '.join(f'[[name:{c["id"]}]] is tagged {h[0]}, which matches your question.' if h[1] == h[0].casefold() else f'For "{h[1]}": [[name:{c["id"]}]] is tagged {h[0]}.' for c, _, h in hits))
    parts.append(f"These do different jobs, so which one are you actually after: [[name:{cs[0]['id']}]] or [[name:{cs[1]['id']}]]?" if different else question.strip())
    return '\n\n'.join(p for p in parts if p)
