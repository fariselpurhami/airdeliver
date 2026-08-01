# apps/api/app/models/product.py

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Dict, Optional, TYPE_CHECKING

from pydantic import field_validator
from sqlalchemy import CheckConstraint, Column, DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB  # <-- L8 Upgrade: استخدام JSONB بدلاً من JSON
from sqlmodel import Field, Relationship, SQLModel

from sqlalchemy.orm import Mapped, relationship

from pydantic import field_validator, field_serializer

if TYPE_CHECKING:
    from .order import OrderItem

class Product(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="check_price_positive"),
        CheckConstraint("inventory >= 0", name="check_inventory_positive"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True, nullable=False, max_length=128)
    name: str = Field(index=True, max_length=255)
    description: str
    price: Decimal = Field(
        default=Decimal("0.00"), 
        sa_column=Column(Numeric(10, 2), nullable=False)
    )
    currency: str = Field(default="USD", max_length=3, nullable=False)
    inventory: int = Field(default=0, nullable=False, ge=0)
    image: Optional[str] = Field(default=None, max_length=2048)
    category: str = Field(default="uncategorized", index=True, max_length=128)
    
    # ---------------------------------------------------------
    # L8 Architecture: JSONB with strict typing and defaults
    # ---------------------------------------------------------
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default='{}')
    )
    tags: List[str] = Field(
        default_factory=list, 
        sa_column=Column(JSONB, nullable=False, server_default='[]')
    )
    # ---------------------------------------------------------

    rating: Optional[float] = Field(default=None, index=True, ge=0.0, le=5.0)
    is_active: bool = Field(default=True, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.now(timezone.utc)
        )
    )

    order_items: Mapped[List["OrderItem"]] = Relationship(
        sa_relationship=relationship("OrderItem", back_populates="product")
    )

    model_config = {"from_attributes": True}

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, value: Any) -> Decimal:
        if isinstance(value, (str, int)):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        return value

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, value: Any) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return value

    @field_serializer("price")
    def serialize_price(self, price: Any, _info: Any) -> str:
        return str(price)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: Any, _info: Any) -> str:
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)
