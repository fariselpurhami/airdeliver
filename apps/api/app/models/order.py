# apps/api/app/models/order.py

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone
from .enums import OrderStatus, CancellationReason

if TYPE_CHECKING:
    from .user import User
    from .drone import Drone
    from .product import Product
    from .audit_trail import AuditTrail
    from .mission import Mission

class Order(SQLModel, table=True):
    __tablename__ = "orders"
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

    # 2. حالة الدفع (الـ Checkout Service يحتاجها لتحديث الحالة لاحقاً)
    is_paid: bool = Field(default=False)
    paid_at: Optional[datetime] = Field(default=None)
    stripe_payment_id: Optional[str] = Field(default=None, nullable=True)
    
    # Diamond Standard: UTC Timezones + Auto Update Logic
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    delivery_address: str = Field(default="")
    delivery_lat: float = Field(default=0.0)
    delivery_lon: float = Field(default=0.0)

    drone_id: Optional[int] = Field(default=None, foreign_key="drones.id", index=True)

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
    mission: Mapped[Optional["Mission"]] = Relationship(
        sa_relationship=relationship("Mission", back_populates="order", uselist=False)
    )
    drone: Mapped[Optional["Drone"]] = Relationship(
        sa_relationship=relationship("Drone", back_populates="assigned_orders")
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
