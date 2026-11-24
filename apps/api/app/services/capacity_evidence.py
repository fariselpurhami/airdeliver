"""Narrow capacity identity, not inferred upgrade or generic spec parsing.

Amounts compare only in the same normalized unit. Explicit English bound
phrases are recognized; no GB/GiB or MB/GB conversion or implied upgrade.
"""
import re
from decimal import Decimal

UNIT=r'(?:megabytes?|gigabytes?|terabytes?|mb|gb|tb|mib|gib|tib)'
KIND=r'(?:ram|memory|storage|ssd|hdd)'
AMOUNT=r'(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>'+UNIT+r')'
PATTERNS=[re.compile(r'^\s*'+AMOUNT+r'\s*(?P<kind>'+KIND+r')\s*$',re.I),
          re.compile(r'^\s*(?P<kind>'+KIND+r')\s*[:=]?\s*'+AMOUNT+r'\s*$',re.I)]
UNITS={'megabyte':'mb','megabytes':'mb','gigabyte':'gb','gigabytes':'gb','terabyte':'tb','terabytes':'tb'}


def capacity_token(text):
    if not isinstance(text,str):return None
    for pattern in PATTERNS:
        match=pattern.fullmatch(text)
        if match:
            amount=Decimal(match['amount']);unit=match['unit'].casefold();kind=match['kind'].casefold()
            if amount<=0:return None
            return ('ram' if kind in {'ram','memory'} else kind,amount,UNITS.get(unit,unit))
    return None


def supported_capacity(feature,specs,name=''):
    comparator='eq'
    literal=feature
    bound=re.fullmatch(r'\s*(at least|minimum|min\.?|at most|maximum|max\.?)\s+(.+?)\s*',feature,re.I) if isinstance(feature,str) else None
    if bound:
        comparator='ge' if bound[1].casefold().rstrip('.') in {'at least','minimum','min'} else 'le'
        literal=bound[2]
    wanted=capacity_token(literal)
    if wanted is None:
        # Recognized bound with unparseable typed value cannot fall through to
        # generic prose matching. Missing evidence fails closed.
        return False if bound else None
    # Preserve literal typed capacity in a current product name as evidence.
    # Reject ambiguous variant/option syntax instead of selecting a maximum.
    if comparator=='eq' and isinstance(name,str) and not re.search(r'\b(?:or|option|options|variant|variants)\b|[/|]',name,re.I):
        normalized=re.sub(r'\s+','',feature.casefold())
        pattern=r'(?<!\w)'+r'\s*'.join(re.escape(c) for c in normalized)+r'(?!\w)'
        if re.search(pattern,name.casefold()):return True
    for key,value in specs.items():
        # An isolated typed value can bind to its own attribute key, never an
        # unrelated adjacent flattened field. Full string must be unambiguous.
        direct=capacity_token(str(value))
        paired=capacity_token(str(key)+' '+str(value))
        for actual in (direct,paired):
            if actual is None or actual[0]!=wanted[0] or actual[2]!=wanted[2]:continue
            if comparator=='eq' and actual[1]==wanted[1]:return True
            if comparator=='ge' and actual[1]>=wanted[1]:return True
            if comparator=='le' and actual[1]<=wanted[1]:return True
    return False
