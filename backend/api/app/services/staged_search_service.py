"""Shared staged retrieval. Tier labels never establish product evidence.

Sequential per-target calls protect AsyncSession. Publication still rehydrates
current SQL rows and applies the customer's complete hard brief.
"""
import asyncio
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class StagedResult:
    candidates: tuple[Any,...]
    tier: str


def _get(row,key,default=None):
    return row.get(key,default) if isinstance(row,Mapping) else getattr(row,key,default)


def _rows(value,limit):
    if not isinstance(value,(list,tuple)):raise ValueError('Invalid retrieval result')
    if len(value)>limit:raise ValueError('Retrieval result exceeds requested limit')
    unique={}
    for row in value:
        pid=_get(row,'id');name=_get(row,'name')
        if type(pid) is int and pid>0 and isinstance(name,str) and 0<len(name)<=1000:
            unique.setdefault(pid,row)
    return tuple(unique.values())


async def staged_search(engine, db, query: str, *, category=None, rank: Callable, broaden: Callable, timeout=5.0) -> StagedResult:
    if not isinstance(query,str) or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=15:
        raise ValueError('Invalid staged search boundary')
    query=' '.join(query.split())
    if not query or len(query)>256:raise ValueError('Invalid staged search query')
    if category is not None and (not isinstance(category,str) or not 0<len(category.strip())<=128):
        raise ValueError('Invalid staged category')
    filters={'category':category} if category else None
    async with asyncio.timeout(timeout):
        high=_rows(await engine.perform_hybrid_search_pure(db,query,limit=30,filters=filters),30)
        terms=set(query.casefold().split())
        exact=[p for p in high if all(t in _get(p,'name').casefold() for t in terms)]
        if exact:
            # Historical price order is diagnostic, never a value/quality claim.
            def price(p):
                try:
                    value=float(_get(p,'price',0) or 0)
                    return value if math.isfinite(value) else 0
                except (ValueError,TypeError,OverflowError):return 0
            return StagedResult(tuple(sorted(exact,key=price,reverse=True))[:5],'high_precision_exact')
        if high:
            ranked=_rows(await asyncio.to_thread(rank,query,list(high)),30)
            allowed={_get(row,'id'):row for row in high}
            # A ranker may reorder/subset, never add or replace retrieval rows.
            return StagedResult(tuple(allowed[_get(row,'id')] for row in ranked if _get(row,'id') in allowed)[:5],'high_precision_ranked')
        # Empty limit30 cannot gain rows by repeating the same query at limit10.
        broad=broaden(query)
        if not isinstance(broad,str):raise ValueError('Invalid broad query')
        broad=' '.join(broad.split())
        if len(broad)>256:raise ValueError('Broad query exceeds boundary')
        if not broad or broad.casefold()==query.casefold():return StagedResult((),'no_match')
        rows=_rows(await engine.perform_hybrid_search_pure(db,broad,limit=5,filters=filters),5)
        return StagedResult(rows,'broad_fallback' if rows else 'no_match')


# Original implementation retained for source continuity, no active callers.
async def _legacy_staged_search_unvalidated(engine, db, query: str, *, category=None, rank: Callable, broaden: Callable, timeout=5.0) -> StagedResult:
    query=' '.join(query.split())
    if not query or len(query)>256 or not 0<timeout<=15:
        raise ValueError('Invalid staged search boundary')
    filters={'category':category} if category else None
    def unique(rows: Sequence[Any]):
        by_id={}
        for row in rows:
            pid=getattr(row,'id',None)
            if type(pid) is int and pid>0:by_id.setdefault(pid,row)
        return tuple(by_id.values())[:5]
    async with asyncio.timeout(timeout):
        high=await engine.perform_hybrid_search_pure(db,query,limit=30,filters=filters)
        terms=set(query.casefold().split())
        exact=[p for p in high if all(t in str(getattr(p,'name','')).casefold() for t in terms)]
        if exact:
            # Preserve historical exact-tier price ordering, not a value claim.
            def price(p):
                try:return float(getattr(p,'price',0) or 0)
                except (ValueError,TypeError):return 0
            return StagedResult(unique(sorted(exact,key=price,reverse=True)),'high_precision_exact')
        if high:
            return StagedResult(unique(await asyncio.to_thread(rank,query,high)),'high_precision_ranked')
        # An empty limit30 result cannot gain candidates by repeating limit10.
        # Retry only when broadening actually changes the query.
        broad=' '.join(broaden(query).split())
        if not broad or broad.casefold()==query.casefold():
            return StagedResult((),'no_match')
        rows=await engine.perform_hybrid_search_pure(db,broad,limit=5,filters=filters)
        return StagedResult(unique(rows),'broad_fallback' if rows else 'no_match')
