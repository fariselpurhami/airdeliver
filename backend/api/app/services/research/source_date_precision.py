"""Inactive strict publication-date parsing, not evidence authentication.

A date-only source stays date-only. No midnight, source timezone, product,
release date, market or publisher trust is inferred. No caller activates this.
"""
from dataclasses import dataclass
from datetime import date,datetime,timedelta
import re
from typing import Literal


@dataclass(frozen=True)
class ParsedPublication:
    raw:str
    precision:Literal['day','instant']
    day:date
    instant:datetime|None=None


def parse_source_publication(raw):
    """Accept explicit ISO shapes while preserving missing time precision.

    Some publishers append Z to a calendar date. That suffix still supplies no
    time of day. Unknown-offset -00:00 is not an established timezone. Modified
    dates and relative prose need independent source-specific semantics.
    """
    try:
        if type(raw) is not str:raise ValueError
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}Z?',raw):
            return ParsedPublication(raw,'day',date.fromisoformat(raw[:10]))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',raw):raise ValueError
        if raw.endswith('-00:00'):raise ValueError
        if not raw.endswith('Z') and int(raw[-2:])>=60:raise ValueError
        instant=datetime.fromisoformat(raw.replace('Z','+00:00'))
        if abs(instant.utcoffset())>timedelta(hours=14):raise ValueError
        return ParsedPublication(raw,'instant',instant.date(),instant)
    except (ValueError,TypeError,OverflowError) as exc:
        raise ValueError('unsupported_publication_date') from exc
