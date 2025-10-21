# app/models/product.py

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from .order import OrderItem

class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    price: float
    inventory: int
    image_url: Optional[str] = None

    order_items: Mapped[List["OrderItem"]] = Relationship(sa_relationship=relationship("OrderItem", back_populates="product"))

    model_config = { "from_attributes": True }
