# apps/api/app/models/order.py (Corrected)

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone
from .enums import OrderStatus

if TYPE_CHECKING:
    from .user import User
    from .drone import Drone
    from .product import Product
    from .audit_trail import AuditTrail
    from .mission import Mission

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")

    status: OrderStatus = Field(
        sa_column=Column(SAEnum(OrderStatus, name="orderstatus", native_enum=False), nullable=False),
        default=OrderStatus.PENDING
    )
    total_price: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                 sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)})

    delivery_address: str = Field(default="")
    delivery_lat: float = Field(default=0.0)
    delivery_lon: float = Field(default=0.0)

    drone_id: Optional[int] = Field(default=None, foreign_key="drones.id")

    user: Mapped["User"] = Relationship(sa_relationship=relationship("User", back_populates="orders"))
    items: Mapped[List["OrderItem"]] = Relationship(
        sa_relationship=relationship("OrderItem", back_populates="order", cascade="all, delete-orphan") 
    )
    mission: Mapped[Optional["Mission"]] = Relationship(
        sa_relationship=relationship("Mission", back_populates="order", uselist=False)
    )
    drone: Mapped[Optional["Drone"]] = Relationship( 
        sa_relationship=relationship("Drone", back_populates="assigned_orders")
    )
    audit_trails: Mapped[List["AuditTrail"]] = Relationship(
        sa_relationship=relationship("AuditTrail", back_populates="order", cascade="all, delete-orphan") 
    )

    model_config = { "from_attributes": True }

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int
    price_per_unit: float 

    order: Mapped["Order"] = Relationship(sa_relationship=relationship("Order", back_populates="items"))
    product: Mapped["Product"] = Relationship(sa_relationship=relationship("Product", back_populates="order_items"))

    model_config = { "from_attributes": True }
