"""Auditable catalog clauses, never unchecked model prose or inferred attributes."""
from decimal import Decimal, InvalidOperation
import json
import math
import re


def number(value):
    if isinstance(value,bool) or value is None:return None
    try:
        result=Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation,ValueError):return None


def amount(value):
    return format(value.quantize(Decimal('.01')),'f')


def price(product):
    value=number(product.get('price'));currency=product.get('currency')
    if (product.get('price_status')=='listed' and value is not None and value>0
        and isinstance(currency,str) and re.fullmatch(r'[A-Z]{3}',currency)):
        return value,currency
    return None


def rating(product):
    value=number(product.get('catalog_rating',product.get('rating')))
    return value if value is not None and 0<=value<=5 else None


def quoted(value):
    if not isinstance(value,str) or not value.strip() or len(value.strip())>64:return None
    return json.dumps(value.strip(),ensure_ascii=False)


def factual_reasons(product,products=(),reference=None):
    clauses=[];value=price(product);score=rating(product)
    category=quoted(product.get('category'))
    if category:clauses.append('Catalog category: '+category+'.')
    if value:
        cost,currency=value;clauses.append(f'Catalog-listed price: {currency} {amount(cost)}.')
        peers=[price(p)[0] for p in products if price(p) and price(p)[1]==currency]
        if len(peers)>1 and cost==min(peers):
            label='Joint-lowest' if peers.count(cost)>1 else 'Lowest'
            clauses.append(f'{label} listed price among {len(peers)} {currency}-priced candidates.')
        if reference and reference.get('id')!=product.get('id'):
            ref=price(reference)
            if ref and ref[1]==currency:
                delta=cost-ref[0]
                if delta:clauses.append(f'{currency} {amount(abs(delta))} '+('less' if delta<0 else 'more')+f' than reference item #{reference["id"]}.')
                else:clauses.append(f'Same listed price as reference item #{reference["id"]}.')
    if score is not None:
        clauses.append(f'Catalog rating: {score}/5.')
        peers=[rating(p) for p in products if rating(p) is not None]
        if len(peers)>1 and score==max(peers):
            label='Joint-highest' if peers.count(score)>1 else 'Highest'
            clauses.append(f'{label} catalog rating among {len(peers)} rated candidates.')
        if reference and reference.get('id')!=product.get('id'):
            ref=rating(reference)
            if ref is not None and score!=ref:
                clauses.append(f'{abs(score-ref)} rating points '+('above' if score>ref else 'below')+f' reference item #{reference["id"]}.')
    attrs=product.get('attributes',{})
    if isinstance(attrs,dict):
        for key in ('material','style','use'):
            text=quoted(attrs.get(key))
            if text:clauses.append(f'Catalog {key}: {text}.')
    # Each option is an exact clause or a complete, bounded multi-clause card.
    if not clauses:return ('Catalog-listed option.',)
    rich=[];size=0
    for clause in clauses:
        if size+len(clause)+1<=600:rich.append(clause);size+=len(clause)+1
    return tuple(clauses)+(' '.join(rich),)


def ground_recommendation_copy(ids,reasons,products,*,compare_to_id=None):
    by_id={p['id']:p for p in products if p.get('id') is not None}
    reference=by_id.get(compare_to_id)
    grounded={}
    for pid in ids:
        allowed=factual_reasons(by_id.get(pid,{}),products,reference)
        proposed=reasons.get(str(pid),'')
        grounded[str(pid)]=proposed if proposed in allowed else allowed[-1]
    noun='option' if len(ids)==1 else 'options'
    intro=(f'{len(ids)} catalog-listed {noun}. Compare the recorded prices, ratings and supplied attributes below. '
           'Selection order is not a verified quality ranking.') if ids else 'No catalog-listed options were selected.'
    return grounded,intro
