from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from .order import OrderItem
    from .ai_cart import AIOrderingCartItem

class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    price: float
    inventory: int
    image_url: Optional[str] = None
    
    category: str = Field(default="uncategorized", index=True)
    tags: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))

    rating: Optional[float] = Field(default=4.5, index=True)

    order_items: Mapped[List["OrderItem"]] = Relationship(sa_relationship=relationship("OrderItem", back_populates="product"))

    ai_cart_items: Mapped[List["AIOrderingCartItem"]] = Relationship(
        sa_relationship=relationship("AIOrderingCartItem", back_populates="product")
    )

    model_config = { "from_attributes": True }
