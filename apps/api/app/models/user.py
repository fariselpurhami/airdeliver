from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Field, JSON, Column
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime
from .notification import Notification

if TYPE_CHECKING:
    from .order import Order
    from .gamification import UserBadge
    from .audit_trail import AuditTrail
    from .notification_subscription import NotificationSubscription


class AIMemory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)

    context_data: Dict[str, Any] = Field(sa_column=Column(JSON))
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, 
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = None
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    role: UserRole = Field(
        default=UserRole.USER,
        sa_column=Column(SAEnum(UserRole, name="userrole", native_enum=False), nullable=False)
    )

    phone_number: Optional[str] = Field(default=None, index=True, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    avatar_url: Optional[str] = Field(default=None, nullable=True)
    stripe_customer_id: Optional[str] = Field(default=None, index=True, nullable=True)

    orders: Mapped[List["Order"]] = Relationship(sa_relationship=relationship("Order", back_populates="user"))
    badges: Mapped[List["UserBadge"]] = Relationship(sa_relationship=relationship("UserBadge", back_populates="user"))
    audit_changes: Mapped[List["AuditTrail"]] = Relationship(sa_relationship=relationship("AuditTrail", back_populates="user"))
    notification_subscription: Mapped[Optional["NotificationSubscription"]] = Relationship(sa_relationship=relationship("NotificationSubscription", back_populates="user"))

    notifications: Mapped[List["Notification"]] = Relationship(
        sa_relationship=relationship(
            "Notification",
            back_populates="user",
            cascade="all, delete-orphan" # (اختياري: لحذف إشعارات المستخدم عند حذفه)
        )
    )

    model_config = { "from_attributes": True }
