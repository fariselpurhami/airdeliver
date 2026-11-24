"""Narrow capacity identity, not inferred upgrade or generic spec parsing.

Amounts must match exactly in the same normalized unit. No GB/GiB or MB/GB
conversion, minimum-capacity inference or alternatives are accepted here.
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


def supported_capacity(feature,specs):
    wanted=capacity_token(feature)
    if wanted is None:return None
    for key,value in specs.items():
        # An isolated typed value can bind to its own attribute key, never an
        # unrelated adjacent flattened field. Full string must be unambiguous.
        direct=capacity_token(str(value))
        paired=capacity_token(str(key)+' '+str(value))
        if wanted in (direct,paired):return True
    return False
