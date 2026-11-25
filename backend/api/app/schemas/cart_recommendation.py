"""Optional read-only cart recommendations, never a cart mutation command."""
from typing import Literal
from pydantic import BaseModel, Field

CART_RECOMMENDATION_ROUTING_KEY = 'airdeliver.ai.cart.recommendation'
CART_RECOMMENDATION_QUEUE = 'q.ai.cart.recommendation'


class CartRecommendationEvent(BaseModel):
    version: Literal[1] = 1
    user_id: int = Field(strict=True, ge=1, le=9223372036854775807)
    product_id: int = Field(strict=True, ge=1, le=9223372036854775807)
    removal_reason: str | None = Field(default=None,max_length=256,strict=True)
    operation: Literal['added', 'removed']
