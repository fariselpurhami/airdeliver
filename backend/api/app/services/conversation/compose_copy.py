"""Compose mode assembler: the model writes an opening and a question, code builds everything between from the cards. Split out of slot_copy.py with no behavior change; slot_copy re-exports every name."""
import re
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from app.services.conversation.slot_errors import SlotError
from app.services.conversation.compose_facts import _listed, _label, _join, _card_words, _grams, _names, _need_lines
from app.services.conversation.compose_asks import _unlisted_asks_in, _UNLISTED_ASKS, _pick, _unlisted_lines, _tag_echoes_card


class ComposeDraft(BaseModel):
    """Compose mode: the model writes only a short opening and one closing question."""
    model_config = ConfigDict(extra='forbid')
    opening: StrictStr = Field(min_length=1, max_length=300)
    question: StrictStr = Field(min_length=1, max_length=240)


COMPOSE_RULES = (
    "You write only two short pieces for a shopping reply; code adds every fact. opening: one or two sentences (at most 35 words) that answer the customer's situation in plain, warm words, like a sharp friend. question: one specific question (at most 25 words) about what matters most to the customer, only about topics the customer wrote or the listed fields (price, weight, rating, tags); never name a use or feature the customer did not mention. When the cards look like two different kinds of item, ask which of them the customer actually needs; never ask whether price is the only factor. "
    "Both pieces must contain no digits, no prices, no measurements, no product features, no praise or ranking (best, better, ideal, perfect, lightweight, great) and no promises about stock, delivery, warranty or returns. You may name a product only as [[name:ID]] with an ID from the supplied cards. Return JSON with keys opening and question only."
)


# Life-stage words and the tag word they imply (a puppy is a dog, a toddler is a kid).
_IMPLIES = {'puppy': 'dog', 'puppies': 'dog', 'kitten': 'cat', 'kittens': 'cat', 'toddler': 'kids', 'toddlers': 'kids', 'baby': 'kids', 'babies': 'kids', 'child': 'kids', 'children': 'kids'}


def compose_text(opening, question, cards, message=None):
    """Compose mode (AIRDELIVER_SLOT_COMPOSE=1): code builds everything between the model's opening and question from the cards alone: one fact block per product and what each card does not list. Only name slots and the card block carry values."""
    cs = [c.model_dump() if hasattr(c, 'model_dump') else dict(c) for c in cards]
    letters = [ch for ch in (message or '') if ch.isalpha()]
    if letters and sum(1 for ch in letters if ord(ch) > 0x24F) / len(letters) > 0.4:
        raise SlotError('compose_non_english')  # the scaffolding is English; the normal writer answers in the customer's language
    allowed = {w[:5] for w in re.findall(r'[a-z]{5,}', (message or '').casefold())}
    for c in cs:
        allowed |= {w[:5] for w in re.findall(r'[a-z]{5,}', str(c.get('name', '')).casefold())}
    strip = lambda t: re.sub(r'\[\[name:\d+\]\]', ' ', t).casefold()
    stripped = strip(f'{opening} {question}')
    if re.search(r'\b(?:free|deliver\w*|ship\w*|warrant\w*|guarant\w*|return\w*|refund\w*|reserv\w*|discount\w*|special offers?|promo\w*|coupon\w*|deals?|stock|available|availability)\b', stripped):
        raise SlotError('compose_policy_wording')
    if re.search(r"\b(?:i|we)(?:\s+(?:can|could|will|shall|would|am going to|may|might)|[\x27’](?:ll|d))\s+(?:also\s+)?(?:check|look|find|verify|confirm|research|dig|get back|follow|search|see|ask|investigate|track|chase|reach|contact)\w*\b|\blet me\s+(?:look into|find out|get back|verify|confirm|dig)\b", stripped):
        raise SlotError('compose_action_offer')
    if re.search(r'\b(?:work|works|working|worked|suit|suits|suited|suitable|fit|fits|fitting|good|ideal|perfect|great|handy|useful|right)\s+(?:for|well|you)\b|\b(?:would|could|will|can)\s+(?:suit|work|fit)\b|\b(?:generally|usually|typically|often|tends?|normally|mostly)\b|\bsuit\w*\b|\bfits?\b', stripped):
        raise SlotError('compose_suitability_claim')
    if re.search(r'\b(?:solid|strong|excellent|nice|awesome|fantastic|amazing|reliable|quality|decent|sturdy|durable|popular|favou?rites?|trusted|top|winners?|smart|wise|well[- ]made|great|good|picks?|choices?|combo|pair|worthy|superb|brilliant|lovely|cool)\b', stripped):
        raise SlotError('compose_praise_wording')
    topics = [m for ask in _unlisted_asks_in(message, cs) for m in [re.search(ask, opening.casefold())] if m]
    if (topics and not re.search(r'\b(?:want to know|wants to know|asking|wondering|curious|whether|looking (?:for|to)|checking|need to know|\byou(?:[\x27’]re| are| want| need| have| mentioned| said| asked| were)|\bif\b)', opening.casefold())) or re.search(r'\bshould\s+(?:be|work|fit|suit)\b', stripped):
        raise SlotError('compose_unlisted_claim')
    words = lambda t: {w[:5] for w in re.findall(r'[a-z]{5,}', t)}
    if words(strip(opening)) & (_card_words(cs) - allowed) or words(strip(question)) & (_card_words(cs, tags=False) - allowed):
        raise SlotError('compose_card_wording')
    listed = {c['id']: _listed(c) for c in cs}
    have = {_label(k) for ks in listed.values() for k in ks} | {'rating' for c in cs if (c.get('catalog_specs') or {}).get('rating')}
    for field in ('weight', 'capacity', 'rating', 'battery', 'material', 'size', 'color', 'colour', 'dimensions', 'warranty', 'price'):
        if re.search(r'\b' + field + r'\b', question.casefold()) and field not in have and not re.search(r'\b' + field + r'\b', (message or '').casefold()):
            raise SlotError('compose_unlisted_field')
    union = []
    for c in cs:
        union += [k for k in listed[c['id']] if k not in union]
    heading = 'Here is what the catalog lists:' if len(cs) == 1 else ('What the catalog lists for each:', 'Here is what each one lists:', 'The listed details, side by side:')[sum(map(ord, message or '')) % 3]
    needs = _need_lines(message, cs)
    low = (message or '').casefold()
    cardkey = 'cardnp' if len(cs) <= 2 and any(n.startswith('On price') for n in needs) else 'card'  # the answer line names two prices only; with 3+ cards the blocks keep theirs
    parts = [' '.join([opening.strip()] + needs)]
    extras = []
    different = False
    keysets = [{k for k in listed[c['id']] if k not in ('price', 'description', 'rating', 'tags')} for c in cs]
    ptypes = [str((c.get('catalog_specs') or {}).get('product_type', '')).strip() for c in cs]
    if len(cs) == 2 and all(ptypes) and ptypes[0].casefold() != ptypes[1].casefold():
        different = True
        parts.append(f"[[name:{cs[0]['id']}]] is listed as [[spec.product_type:{cs[0]['id']}]] and [[name:{cs[1]['id']}]] as [[spec.product_type:{cs[1]['id']}]], {_pick(message, "kind", ("so they are different kinds of item, not substitutes.", "so they are different kinds of product and do not replace each other.", "so they are different kinds of thing, not alternatives to each other."))}")
    elif len(cs) == 2 and all(keysets) and not (keysets[0] & keysets[1]):
        names = [f"[[name:{c['id']}]]" for c in cs]
        different = True
        extras.append(f"{names[0]} is listed with {_join([_label(k) for k in sorted(keysets[0])])} and {names[1]} with {_join([_label(k) for k in sorted(keysets[1])])}, {_pick(message, "kind", ("so they look like two different kinds of item, not substitutes.", "so they are not interchangeable.", "so they are not really alternatives to each other."))}")
    elif len(cs) == 2:
        cats = [str(c.get('category') or '').strip() for c in cs]
        if all(cats) and not any(x.casefold() == 'uncategorized' for x in cats) and cats[0].casefold() != cats[1].casefold():
            different = True
            extras.append(f"[[name:{cs[0]['id']}]] is listed under {cats[0]} and [[name:{cs[1]['id']}]] under {cats[1]}, {_pick(message, "kind", ("so they look like two different kinds of item, not substitutes.", "so they are not interchangeable.", "so they are not really alternatives to each other."))}")
    parts.append(heading + '\n' + '\n'.join(f"- [[{cardkey}:{c['id']}]]" for c in cs))
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
        extras.append(' '.join(gaps))
    unlisted = _unlisted_lines(message, cs)
    if unlisted:
        extras.append(' '.join(unlisted))
    qwords = {w for w in re.findall(r'[a-z]{4,}', low)}
    fits = []
    for c in cs:
        tags = [x.strip() for x in str((c.get('catalog_specs') or {}).get('tags', '')).split(',') if len(x.strip()) >= 4 or x.strip().casefold() in _IMPLIES.values()]
        hit = None
        for tag in tags:
            word = next((w for w in sorted(qwords) if w[:3] == tag.casefold()[:3] or _IMPLIES.get(w, '')[:3] == tag.casefold()[:3]), None)
            if word and (tag.casefold() not in str(c.get('name', '')).casefold() or word in _IMPLIES):
                hit = (tag, word)
                break
        fits.append((c, tags, hit))
    hits = [f for f in fits if f[2]]
    if hits:
        word = hits[0][2][1]
        others = [f for f in fits if not f[2] and f[1] and not any(g[:3] == word[:3] for g in (x.casefold() for x in f[1]))]
        if len(hits) == len(cs) >= 2 and not others and len({h[2][0].casefold() for h in hits}) == 1:  # one line, not one per card
            extras.append(f'{"Both are" if len(cs) == 2 else "All of them are"} tagged {hits[0][2][0]}.')
        elif others or len(hits) > 1:
            seg = [f'- [[name:{c["id"]}]] is tagged {h[0]}.' for c, _, h in hits] + [f'- [[name:{c["id"]}]] has no matching tag' + ('.' if _tag_echoes_card(c, tags) else f' (its tags: {", ".join(tags)}).') for c, tags, _ in others]
            extras.append(f'For "{word}":\n' + '\n'.join(seg))
        else:
            extras.append(' '.join(f'[[name:{c["id"]}]] is tagged {h[0]}, which matches your question.' if h[1] == h[0].casefold() else f'For "{h[1]}": [[name:{c["id"]}]] is tagged {h[0]}.' for c, _, h in hits))
    synthesis = _join_synthesis(extras)
    if synthesis:
        parts.append(synthesis)
    else:  # no notes apply: keep four sections by giving the heading its own paragraph
        parts[1:2] = parts[1].split('\n', 1)
    pair = f"[[name:{cs[0]['id']}]] or [[name:{cs[1]['id']}]]" if len(cs) >= 2 else ''
    parts.append(_pick(message, 'closer', (f'These do different jobs, so which one are you actually after: {pair}?', f'Since they do different jobs, which one do you actually want: {pair}?', f'They cover different needs, so which are you after: {pair}?')) if different else question.strip())
    return '\n\n'.join(p for p in parts if p)


def _join_synthesis(pieces):
    # the reply has four sections: opening, the cards, one synthesis paragraph, the closing question
    out = ''
    for p in (x for x in pieces if x):
        out = p if not out else out + ('\n' if '\n' in out or '\n' in p else ' ') + p
    return out


_NEUTRAL_OPENINGS = ('You want a straight answer, so here it is.', 'Let us take this one piece at a time.', 'Here is how this lines up against what you asked.')
_NEUTRAL_QUESTIONS = ('What matters most to you here?', 'Is there anything else you want to know?', 'What else would you like to know?')


def compose_text_safe(opening, question, cards, message=None):
    """compose_text, but wording the checks reject (an unlisted claim, a field the card lacks) never sends the reply to the free writer: code swaps in a neutral opening and question and keeps every fact it builds from the cards. Real run b052 published an unsupported induction claim through that fallback."""
    try:
        return compose_text(opening, question, cards, message)
    except SlotError as exc:
        if str(exc) == 'compose_non_english':
            raise
        return compose_text(_pick(message, 'open', _NEUTRAL_OPENINGS), _pick(message, 'ask', _NEUTRAL_QUESTIONS), cards, message)
