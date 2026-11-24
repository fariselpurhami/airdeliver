"""Shared staged search, preserving the existing NLU tier semantics.

Sequential per-target calls protect the caller's AsyncSession. Results remain
untrusted retrieval candidates; publication must rehydrate SQL evidence. Tier
labels are diagnostics, not proof of identity, stock, compatibility or quality.
"""
import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class StagedResult:
    candidates: tuple[Any,...]
    tier: str


async def staged_search(engine, db, query: str, *, category=None, rank: Callable, broaden: Callable, timeout=5.0) -> StagedResult:
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
