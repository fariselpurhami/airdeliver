from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from datetime import datetime

if TYPE_CHECKING:
    from .user import User
    from .product import Product

class AIOrderingCartItem(SQLModel, table=True):
    
    __tablename__ = "ai_ordering_cart_items"

    id: Mapped[int] = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True)
    )

    user_id: Mapped[int] = Field(
        sa_column=Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    )

    product_id: Mapped[int] = Field(
        sa_column=Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    )

    quantity: Mapped[int] = Field(
        default=1,
        sa_column=Column(Integer, default=1, nullable=False)
    )

    added_at: Mapped[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    
    
    user: Mapped["User"] = Relationship(
        sa_relationship=relationship("User", back_populates="ai_cart_items")
    )
    
    product: Mapped["Product"] = Relationship(
        sa_relationship=relationship("Product", back_populates="ai_cart_items")
    )

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }
