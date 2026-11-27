"""Compose mode, wording helpers: the not-listed lexicon, deterministic variant picking and the tag-echo test. Split out of slot_copy.py with no behavior change."""
import re
from app.services.conversation.compose_facts import _join


# Common asks a card may not cover: (label, words in the customer's message, words that mean the card text covers it).
_UNLISTED_ASKS = (
    ('waterproofing', r'water.?proof|water.?resistan|swim', r'water.?proof|water.?resistan'),
    ('colour options', r'colou?rs?\b|\b(?:red|blue|green|black|white|pink|gr[ae]y|yellow|brown|purple|orange|beige|navy)\b', r'colou?r'),
    ('compatibility details', r'compatib|work with|works with|fit my|fits my|will (?:this|it) fit|\bandroid\b|\biphone\b|\bsamsung\b|\bmacbook\b|\bps5\b|\bmonitors?\b', r'compatib|works with|\bfits\b'),
    ('noise cancelling', r'noise|cancel', r'noise|cancel'),
    ('a microphone', r'\bmic\b|microphone', r'\bmic\b|microphone'),
    ('bulb or dimming details', r'dimm|bulb', r'dimm|bulb'),
    ('induction use', r'induction', r'induction'),
    ('microwave use', r'microwave', r'microwave'),
    ('care instructions', r'washab|machine.?wash|dishwasher', r'wash|dishwasher|care'),
    ('safety or certification details', r'safe for|safety|standards?\b|certif', r'safe|certif|standard'),
    ('skin or allergy details', r'sensitive skin|allerg|itch|irritat', r'sensitive|allerg|hypoaller|itch|irritat'),
    ('sizing guidance', r'true to size|runs (?:small|large)', r'true to size|runs (?:small|large)'),
    ('warranty or return terms', r'warrant|return polic|refund|exchange', r'warrant|return|refund'),
    ('delivery times or stock', r'deliver|arrive|shipping|in stock|\bstock\b', r'deliver|ship'),
    ('battery life', r'battery|how long (?:does|will) it last|runtime', r'battery'),
)


def _pick(message, salt, options):
    """Deterministic variant by the customer's own message: the same message always gets the same wording, different messages spread over the options."""
    import zlib
    return options[zlib.crc32(f'{salt}|{message or ""}'.encode('utf-8')) % len(options)]


def _unlisted_asks_in(message, cs):
    """The asks in the customer's message that no card text covers (regex of the customer's words). The model's own opening and question may not touch these topics."""
    low = (message or '').casefold()
    covered = ' '.join(
        ' '.join([str(c.get('name', ''))] + [f'{k} {v}' for k, v in (c.get('catalog_specs') or {}).items()]).casefold() for c in cs)
    return [ask for _, ask, have in _UNLISTED_ASKS if low and re.search(ask, low) and not re.search(have, covered)]


def _unlisted_lines(message, cs):
    """Say plainly what the customer asked about that no card text covers. Only the lexicon above, only when no card's own text or spec names it."""
    low = (message or '').casefold()
    if not low:
        return []
    covered = ' '.join(
        ' '.join([str(c.get('name', ''))] + [f'{k} {v}' for k, v in (c.get('catalog_specs') or {}).items()]).casefold() for c in cs)
    missing = []
    for label, ask, have in _UNLISTED_ASKS:
        if re.search(ask, low) and not re.search(have, covered):
            word = re.search(ask, low).group(0)
            if label == 'colour options' and word in covered:
                continue
            missing.append(label)
    if not missing:
        return []
    named = missing[0] if len(missing) == 1 else ', '.join(missing[:-1]) + ' or ' + missing[-1]
    if len(cs) == 1:
        n = f"[[name:{cs[0]['id']}]]"
        return [_pick(message, 'unl1', (f"The entry for {n} doesn't mention {named}.", f"The entry for {n} says nothing about {named}.", f"Nothing in the catalog entry for {n} covers {named}."))]
    return [_pick(message, 'unln', (f'None of these entries mention {named}.', f'Nothing in these entries covers {named}.', f'These entries say nothing about {named}.'))]



def _tag_echoes_card(card, tags):
    """True when a listed spec value appears in the card's name and again in its tags, so one line would carry that value twice (slot_duplicate_value)."""
    name = str(card.get('name', '')).casefold()
    joined = ' '.join(tags).casefold()
    for value in (card.get('catalog_specs') or {}).values():
        v = str(value).strip().casefold()
        if v and re.search(r'(?<![\w])' + re.escape(v) + r'(?![\w])', name) and re.search(r'(?<![\w])' + re.escape(v) + r'(?![\w])', joined):
            return True
    return False
