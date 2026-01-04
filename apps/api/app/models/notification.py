# apps/api/app/models/notification.py

from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum, JSON, Index
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone
from .enums import NotificationType

if TYPE_CHECKING:
    from .user import User
    from .order import Order
    from .drone import Drone

class NotificationBase(SQLModel):
    title: str = Field(index=True)
    body: str
    type: NotificationType = Field(
        sa_column=Column(
            SAEnum(NotificationType, name="notification_type_enum", native_enum=False),
            nullable=False
        )
    )
    read: bool = Field(default=False)
    
    # Global Standard: Use UTC aware datetime
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"
    # Composite index for performance on "Unread Notifications" queries
    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "read", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)

    related_order_id: Optional[int] = Field(default=None, foreign_key="orders.id", nullable=True)
    related_drone_id: Optional[int] = Field(default=None, foreign_key="drones.id", nullable=True)

    meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    user: Mapped["User"] = Relationship(
        sa_relationship=relationship("User", back_populates="notifications")
    )

    order: Mapped[Optional["Order"]] = Relationship(sa_relationship=relationship("Order"))
    drone: Mapped[Optional["Drone"]] = Relationship(sa_relationship=relationship("Drone"))

    model_config = { "from_attributes": True }
