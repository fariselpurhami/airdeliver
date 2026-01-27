# apps/api/app/models/product.py

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from decimal import Decimal
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import Numeric, CheckConstraint
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from .order import OrderItem


class Product(SQLModel, table=True):
    __tablename__ = "products"
    # Hardware/Business Logic Constraint: Price and Inventory cannot be negative
    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_positive'),
        CheckConstraint('inventory >= 0', name='check_inventory_positive'),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # SKU is mandatory for Global Logistics (Stock Keeping Unit)
    sku: str = Field(unique=True, index=True, nullable=False)
    
    name: str = Field(index=True)
    description: str
    
    # FINANCIAL HARDENING: Never use Float for money. Use Decimal(10, 2)
    price: Decimal = Field(default=0.0, sa_column=Column(Numeric(10, 2), nullable=False))
    
    # 🔥 [Architectural Fix 1] Added Currency Field
    currency: str = Field(default="USD", max_length=10, nullable=False, description="ISO 4217 Currency Code")

    inventory: int = Field(default=0, nullable=False)
    
    # 🔥 [Architectural Fix 2] Renamed from image_url to image to match Seeder & DB Schema
    image: Optional[str] = Field(default=None)
    
    category: str = Field(default="uncategorized", index=True)
    
    # Store tags as JSONB for high-performance querying
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))

    rating: Optional[float] = Field(default=4.5, index=True)
    
    is_active: bool = Field(default=True, index=True) # Soft delete capability

    # Audit Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    order_items: Mapped[List["OrderItem"]] = Relationship(
        sa_relationship=relationship("OrderItem", back_populates="product")
    )

    model_config = {"from_attributes": True}
