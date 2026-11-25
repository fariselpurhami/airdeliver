"""Literal non-capacity evidence, not a general attribute/units interpreter.

Each field is isolated. Attribute labels with false/unknown values are not
positive evidence. No cross-field phrases or physical-unit conversions.
"""
import re


def literal_present(term,specs,name='',category=''):
    chars=re.sub(r'\s+','',str(term).casefold())
    if not chars:return False
    pattern=r'(?<!\w)'+r'\s*'.join(re.escape(c) for c in chars)+r'(?!\w)'
    def matches(value):return bool(re.search(pattern,str(value).casefold()))
    if any(matches(value) for value in (name,category)):return True
    unknown={'false','no','none','null','unknown','not verified','unverified','n/a','0','unsupported','not supported'}
    for key,value in specs.items():
        text=str(value).strip()
        if text.casefold() in unknown:continue
        # Negated/variant prose does not prove the selected product has a feature.
        if re.search(r'\b(?:no|not|without|non|or|optional|option|options|variant|variants)\b|[/|]',text,re.I):continue
        if matches(text):return True
        if text.casefold() in {'true','yes','supported'} and matches(key):return True
    return False
