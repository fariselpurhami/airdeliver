"""Quick-tap refinement chips built only from listed catalog facts.

Each chip names the products that justify it. Nothing here is model output, and
no category, price or claim is invented. Not wired into any response path yet.
"""
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.ai_actions import CatalogResult


class RefinementChip(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    kind: Literal['category', 'price_cap']
    label: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=64)
    send_text: str = Field(min_length=1, max_length=120)
    source_product_ids: tuple[int, ...] = Field(min_length=1)


def refinement_chips(cards: list[CatalogResult], brief, limit: int = 4) -> list[RefinementChip]:
    if len(cards) < 2:
        return []
    chips: list[RefinementChip] = []
    seen: dict[str, list[int]] = {}
    for card in cards:
        cat = (card.category or '').strip()
        if cat and cat.casefold() != 'uncategorized':
            seen.setdefault(cat, []).append(card.id)
    if len(seen) >= 2:
        for cat, ids in list(seen.items())[:3]:
            chips.append(RefinementChip(kind='category', label=cat, value=cat,
                                        send_text=f'Show me {cat}', source_product_ids=tuple(ids)))
    if getattr(brief, 'budget_max', None) is None:
        priced = []
        for card in cards:
            try:
                if card.price_status == 'listed' and card.price is not None and card.currency:
                    cost = Decimal(card.price)
                    if cost.is_finite():
                        priced.append((cost, card.price, card.currency, card.id))
            except (InvalidOperation, TypeError, ValueError):
                pass
        if len({p[2] for p in priced}) == 1 and len({p[0] for p in priced}) >= 3:
            priced.sort(key=lambda p: p[0])
            cap = priced[(len(priced) - 1) // 2]
            ids = tuple(p[3] for p in priced if p[0] <= cap[0])
            chips.append(RefinementChip(kind='price_cap', label=f'Up to {cap[1]} {cap[2]}', value=cap[1],
                                        send_text=f'Show me options up to {cap[1]} {cap[2]}', source_product_ids=ids))
    return chips[:max(0, limit)]
