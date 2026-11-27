"""Compose mode, facts the code answers from listed card values only: price, budget, rating and weight lines. Split out of slot_copy.py with no behavior change."""
import re
from decimal import Decimal


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
    cap = re.search(r'(?:under|below|less than|max(?:imum)?|within|up to|at most|no more than)\s*(?:\$|usd|€|£)?\s*(\d+(?:[.,]\d+)?)|(?:\$|€|£)\s*(\d+(?:[.,]\d+)?)\s*(?:or less|max|tops)?|(?:i have|i[\u2019\']ve got|budget(?: is| of)?|spend|limit(?: is| of)?)\s*(?:of\s*)?(?:\$|usd|€|£)?\s*(\d+(?:[.,]\d+)?)', low)
    if cap and re.search(r'[$€£]|usd|dollars?|euros?|pounds?|bucks?|budget', low) and re.search(r'under|below|less than|max|within|up to|at most|no more than|or less|tops|i have|i[\u2019\']ve got|budget|spend|limit', low):
        try:
            limit = Decimal((cap.group(1) or cap.group(2) or cap.group(3)).replace(',', '.'))
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
