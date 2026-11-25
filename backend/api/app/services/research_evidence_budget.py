"""Local bounded evidence windows. Never generate facts or alter quote text."""
import re

def pack_sources(sources, question, targets=(), byte_budget=2400):
    if not sources:
        return []
    terms = set(re.findall(r'\w+', question.casefold()))
    for target in targets:
        terms.update(re.findall(r'\w+', target.casefold()))
    per_source = max(1, byte_budget // len(sources))
    packed = []
    for source in sources:
        text = source['text']
        if len(text.encode('utf-8')) <= per_source:
            packed.append(dict(source))
            continue
        # Score local contiguous windows only. This is evidence selection, not
        # a product-answer heuristic. Source validation and independent model
        # review still decide whether evidence supports the exact product.
        starts = [0] + [m.start() for m in re.finditer(r'\b\w+', text)]
        best = ''
        best_score = -1
        for start in starts:
            window = text[start:start + per_source].encode('utf-8')[:per_source].decode('utf-8', errors='ignore')
            words = re.findall(r'\w+', window.casefold())
            score = 2 * len(terms.intersection(words)) + int(bool(words) and words[0] in terms)
            if score > best_score:
                best, best_score = window, score
        packed.append({**source, 'text': best})
    return packed
