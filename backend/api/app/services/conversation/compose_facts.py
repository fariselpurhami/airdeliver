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
    if len(cs) >= 4:
        low += ' lowest price top rated'  # four or more cards: always give the lowest price and highest rating pointers
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
        mult = quantity_of(message) or 1
        if limit is not None and mult > 1 and priced:
            fit = [i for v, i in priced if v * mult <= limit]
            over = [i for v, i in priced if v * mult > limit]
            nm = lambda ids: _join([f'[[name:{i}]]' for i in ids])
            out.append((f'At your quantity, {nm(fit)} stays within your budget' + (f' and {nm(over)} goes over it.' if over else '.')) if fit else f'At your quantity, {nm(over)} ' + ('goes' if len(over) == 1 else 'go') + ' over your budget.')
        elif limit is not None and len(priced) >= 2:
            fit = [i for v, i in priced if v <= limit]
            over = [i for v, i in priced if v > limit]
            if fit:
                text = 'Within your budget: ' + ' and '.join(f'[[name:{i}]] at [[price:{i}]]' for i in fit) + '.'
                if over:
                    text += ' ' + ' and '.join(f'[[name:{i}]] at [[price:{i}]]' for i in over) + (' is' if len(over) == 1 else ' are') + ' over it.'
                out.append(text)
            else:
                out.append(f'None of these is within your budget; the lowest listed is [[name:{priced[0][1]}]] at [[price:{priced[0][1]}]].')
    qty = quantity_of(message)
    if qty and 1 <= len(cs) <= 3 and all(c.get('price') not in (None, '') for c in cs):
        out.append(('Worked out for you: ', 'The totals: ', 'For that many: ')[__import__('zlib').crc32(f'qty|{message or ""}'.encode('utf-8')) % 3] + '; '.join(f"[[name:{c['id']}]] comes to [[qty:{c['id']}]]" for c in cs) + '.')
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


_NUMWORDS = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'twelve': 12, 'dozen': 12}


def quantity_of(message):
    """How many units the customer says they want ("4 of these", "buy 3", "x5", "a dozen of them"), 2 to 99, else None. Plain counts of other things ("4 kids", "3 hours") do not match."""
    low = (message or '').casefold()
    num = r'(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten|twelve|a dozen)'
    m = (re.search(r'\b' + num + r'\s+(?:of\s+(?:these|them|those|it|the|this)\b|units?\b|pieces?\b|pcs\b|pairs?\b|sets?\b|copies\b)', low)
         or re.search(r'\b(?:buy|order|get|need|want|take)\s+' + num + r'\b(?!\s*(?:hours?|days?|years?|kids?|people|months?|weeks?|minutes?))', low)
         or re.search(r'\bx\s?(\d{1,2})\b|\b(\d{1,2})\s?x\b', low))
    if not m:
        return None
    raw = next(g for g in m.groups() if g)
    n = int(raw) if raw.isdigit() else _NUMWORDS.get(raw.replace('a ', ''))
    return n if n and 2 <= n <= 99 else None


def quantity_numbers(message, cards):
    """Number tokens a quantity line may print for these cards: the count and each card total. Used by the number check."""
    n = quantity_of(message)
    out = set()
    if not n:
        return out
    for c in cards:
        try:
            price = Decimal(str(c['price'] if isinstance(c, dict) else c.price))
        except Exception:
            continue
        out |= {str(n), str((price * n).quantize(Decimal('0.01')))}
    return out
