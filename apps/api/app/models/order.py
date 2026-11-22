# apps/api/app/models/order.py

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, DateTime, Index, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone
from .enums import OrderStatus, CancellationReason

if TYPE_CHECKING:
    from .user import User
    from .product import Product
    from .audit_trail import AuditTrail

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (Index("uq_orders_user_checkout_request", "user_id", "checkout_request_id", unique=True),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    status: OrderStatus = Field(
        default=OrderStatus.PENDING,  # أو CREATED حسب الـ Enum عندك
        sa_column=Column(
            SAEnum(OrderStatus, name="orderstatus", native_enum=False), 
            nullable=False,
            index=True  # 👈 التصحيح: الفهرس مكانه الصحيح هنا
        )
    )

    total_price: float = Field(default=0.0, nullable=False)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    shipping_address_data: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    checkout_request_id: Optional[str] = Field(default=None, max_length=36)
    checkout_fingerprint: Optional[str] = Field(default=None, max_length=64)
    checkout_data: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    payment_setup_generation: int = Field(default=0)
    payment_setup_lease_until: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    # 2. حالة الدفع (الـ Checkout Service يحتاجها لتحديث الحالة لاحقاً)
    is_paid: bool = Field(default=False)
    paid_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    stripe_payment_id: Optional[str] = Field(default=None, nullable=True)
    payment_transaction_id: Optional[str] = Field(default=None, max_length=255, nullable=True)
    

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)),
    )
    

    delivery_address: str = Field(default="")
    delivery_lat: float = Field(default=0.0)
    delivery_lon: float = Field(default=0.0)

    cancellation_reason: Optional[CancellationReason] = Field(
        sa_column=Column(
            SAEnum(CancellationReason, name="cancellation_reason_enum", native_enum=False),
            nullable=True
        ),
        default=None,
    )
    recovery_token: Optional[str] = Field(default=None, index=True, nullable=True)

    user: Mapped["User"] = Relationship(
        sa_relationship=relationship("User", back_populates="orders")
    )
    items: Mapped[List["OrderItem"]] = Relationship(
        sa_relationship=relationship(
            "OrderItem", back_populates="order", cascade="all, delete-orphan"
        )
    )
    audit_trails: Mapped[List["AuditTrail"]] = Relationship(
        sa_relationship=relationship(
            "AuditTrail", back_populates="order", cascade="all, delete-orphan"
        )
    )

    model_config = {"from_attributes": True}


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int
    price_per_unit: float

    order: Mapped["Order"] = Relationship(
        sa_relationship=relationship("Order", back_populates="items")
    )
    product: Mapped["Product"] = Relationship(
        sa_relationship=relationship("Product", back_populates="order_items")
    )

    model_config = {"from_attributes": True}
