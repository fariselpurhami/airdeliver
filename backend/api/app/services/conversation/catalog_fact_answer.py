"""Deterministic answers for a few narrow catalog-fact questions.

Only whole-sentence patterns about exactly one supplied catalog card are
handled: its listed price, a listed attribute value, or a closed set of topics
the card does not list (warranty, shipping, delivery speed, waterproofing).
Everything else returns None and continues on the reviewed model path, so
nothing here can confirm an unlisted claim or invent a product fact.
"""
import re

TOPICS = ('warranty', 'free shipping', 'next day delivery', 'same day delivery',
          'waterproof', 'water resistant', 'free returns')
_TOPIC_KEYS = {'warranty': ('warrant',), 'free shipping': ('ship',), 'next day delivery': ('deliver', 'ship'),
               'same day delivery': ('deliver', 'ship'), 'waterproof': ('waterproof', 'water'),
               'water resistant': ('waterproof', 'water'), 'free returns': ('return',)}


def _clean(text):
    return re.sub(r'\s+', ' ', text.strip().casefold().replace('\u2019', "'")).rstrip('?!. ')


def catalog_fact_answer(question, cards):
    if not isinstance(question, str) or len(question) > 200 or len(cards) != 1:
        return None
    card = cards[0]
    name = card.name.strip()
    if not name:
        return None
    q = _clean(question)
    n = re.escape(name.casefold())
    if re.fullmatch(rf"how much (?:does|is|do|are) (?:the )?{n}(?: cost)?|what(?:'s| is) the price of (?:the )?{n}|what does (?:the )?{n} cost", q):
        if card.price_status == 'listed' and card.price and card.currency:
            return f"The {name} is listed at {card.price} {card.currency} in the catalog. Stock and delivery are not confirmed by this price."
        return f"The catalog does not list a price for the {name}."
    facts = {str(k).casefold(): str(v) for k, v in {**card.attributes, **card.catalog_specs}.items()}
    m = re.fullmatch(rf"what(?:'s| is) the (listed )?([a-z][a-z ]{{1,30}}?) of (?:the )?{n}", q)
    if m:
        key = m.group(2).strip()
        if key in facts:
            return f"The catalog lists the {key} of the {name} as {facts[key]}."
        if m.group(1):
            return f"The catalog does not list the {key} of the {name}."
        return None
    alt = '|'.join(re.escape(t) for t in TOPICS)
    m = re.fullmatch(rf"(?:does|do|is|will) (?:the )?{n} (?:come with |have |include |offer )?(?:a |an )?({alt})", q)
    if m:
        topic = m.group(1)
        haystack = ' '.join([*facts.keys(), *facts.values()])
        if any(k in haystack for k in _TOPIC_KEYS[topic]):
            return None
        return f"The catalog does not list {topic} for the {name}, so I cannot confirm it. Please check with the merchant."
    return None
