"""Bounded LLM editorial selection with auditable item-bound claims."""
import json
from app.services.recommendation_copy import factual_reasons

CONNECTORS={'space':' ','also':' Also, ','meanwhile':' Meanwhile, '}


def claim_catalog(products):
    claims={}
    for product in products[:8]:
        pid=product.get('id')
        if not isinstance(pid,int) or isinstance(pid,bool) or pid<=0:continue
        name=product.get('name')
        if isinstance(name,str) and name.strip() and len(name)<=120:
            claims[f'{pid}:name']=f'Catalog item: {json.dumps(name,ensure_ascii=False)}.'
        for index,clause in enumerate(factual_reasons(product,products)[:-1]):
            if len(clause)<=180:claims[f'{pid}:fact:{index}']=clause
    return claims


def validate_editorial(payload,claims):
    if not isinstance(payload,dict) or set(payload)!={'content','reason'}:raise ValueError('Invalid editorial schema')
    output=[]
    for field in ('content','reason'):
        sections=payload[field]
        if not isinstance(sections,list) or not 1<=len(sections)<=3:raise ValueError('Invalid clause count')
        text=[];seen=set()
        for section in sections:
            if not isinstance(section,dict) or set(section)!={'claim_id','connector'}:raise ValueError('Invalid claim binding')
            key=section['claim_id'];connector=section['connector']
            if not isinstance(key,str) or key not in claims or key in seen:raise ValueError('Unverified claim')
            if not isinstance(connector,str) or connector not in CONNECTORS:raise ValueError('Unverified language')
            seen.add(key);text.append(('' if not text else CONNECTORS[connector])+claims[key])
        rendered=''.join(text)
        if len(rendered)>600:raise ValueError('Editorial copy limit exceeded')
        output.append(rendered)
    if output[0]==output[1]:raise ValueError('Editorial sections must be distinct')
    return tuple(output)


def factual_editorial_fallback(products):
    clauses=[factual_reasons(p,products)[-1] for p in products[:3]]
    return ('Explore these catalog-listed items. No search preferences have been assumed.',
            ' '.join(clauses)[:600] if clauses else 'No catalog facts available for this row.')


def opening_editorial(products):
    """Restore the original row-template presentation, bound to this row only.

    Editorial framing is not a quality, personalization or popularity claim.
    Names and money come from the same sanitized records as the shown cards.
    """
    from app.services.recommendation_copy import price, amount
    import re
    def label(value,limit=120):
        if not isinstance(value,str):return None
        value=' '.join(value.split())
        if not value or len(value)>limit or re.search(r'[<>\x00-\x1f]',value):return None
        return value
    def join(values):
        if len(values)==1:return values[0]
        return ', '.join(values[:-1])+' and '+values[-1]
    items=[p for p in products[:8] if isinstance(p,dict)]
    if not items:return ('Explore the collection.','No items are available in this selection yet.')
    categories=list(dict.fromkeys(v for p in items if (v:=label(p.get('category'),64))))
    brands=list(dict.fromkeys(v for p in items if (v:=label(p.get('brand'),64))))
    names=[v for p in items if (v:=label(p.get('name')))]
    focus=join(categories[:4]) if 0<len(categories)<=4 else 'the pieces shown here'
    content=f'A curated selection of {focus}, brought together in one considered edit.'
    # Original rhythm retained, unsupported lifestyle effects intentionally absent.
    reason=f'This edit brings together {join(names[:8])}.' if names else 'Explore the individual pieces in the cards above.'
    prices=[price(p) for p in items]
    if all(prices) and len({entry[1] for entry in prices})==1:
        currency=prices[0][1];values=[entry[0] for entry in prices]
        cost=f'{currency} {amount(min(values))}'
        if min(values)!=max(values):cost+=f' to {currency} {amount(max(values))}'
        reason+=f' The displayed selection is priced at {cost}.'
    if brands and len(brands)<=4:
        content=f'A curated selection from {join(brands)}, brought together in one considered edit.'
        if categories and len(categories)<=4:content+=f' Explore {join(categories)}.'
    return content,reason
