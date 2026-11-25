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
    Categories and brands come from the same sanitized records as the shown cards.
    """
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
    focus=join(categories[:4]) if 0<len(categories)<=4 else 'the pieces shown here'
    content=f'A curated selection of {focus}, brought together in one considered edit.'
    # Guidance is an invitation, never an assertion that the pieces match or
    # have an unlisted quality. Prices remain on the product cards only.
    category_keys={value.casefold() for value in categories}
    if category_keys == {'clothing','accessories'}:
        reason=('Begin with the clothing that sets your direction, then consider the accessories as finishing touches. '
                'Build around a piece you love, rather than treating the edit as a prescribed look.')
    elif category_keys == {'clothing'}:
        reason=('Begin with the piece you would build a look around. '
                'Consider how each choice could sit alongside what you already wear, rather than treating the edit as a complete outfit.')
    elif category_keys == {'accessories'}:
        reason=('Consider the detail you want to make your own. '
                'Explore each accessory as a finishing touch to what you already wear, without needing to choose the whole edit.')
    elif len(category_keys)>1:
        reason=('Different categories leave room for different directions. '
                'Consider each piece on its own merits, and choose what has a place in your everyday life. There is no need to make the whole edit yours.')
    else:
        reason=('Start with the piece that draws your attention. '
                'Explore its details and consider how you would use it, choosing what has a place in your life rather than choosing the whole edit.')
    if brands and len(brands)<=4:
        content=f'A curated selection from {join(brands)}, brought together in one considered edit.'
        if categories and len(categories)<=4:content+=f' Explore {join(categories)}.'
    return content,reason
