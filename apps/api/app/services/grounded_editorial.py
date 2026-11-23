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
