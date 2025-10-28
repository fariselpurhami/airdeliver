# file: airdeliver/apps/api/app/models/user.py (Corrected)

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime
from pydantic import EmailStr

# Import Enum from the dedicated file
from .enums import UserRole

# Forward references for relationships
if TYPE_CHECKING:
    from .order import Order
    from .gamification import UserBadge
    from .audit_trail import AuditTrail
    from .notification_subscription import NotificationSubscription
    from .notification import Notification
    from .aimemory import AIMemory

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = None
    email: EmailStr = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    role: UserRole = Field(
        default=UserRole.USER,
        sa_column=Column(SAEnum(UserRole, name="userrole", native_enum=False), nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Contact and Address Info
    phone_number: Optional[str] = Field(default=None, index=True, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    country: Optional[str] = Field(default=None, nullable=True)
    avatar_url: Optional[str] = Field(default=None, nullable=True)

    # External Service IDs
    stripe_customer_id: Optional[str] = Field(default=None, index=True, nullable=True)

    # Relationships defined using Mapped and sa_relationship
    orders: Mapped[List["Order"]] = Relationship(
        sa_relationship=relationship("Order", back_populates="user", cascade="all, delete-orphan")
    )
    badges: Mapped[List["UserBadge"]] = Relationship(
        sa_relationship=relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    )
    audit_changes: Mapped[List["AuditTrail"]] = Relationship(
        sa_relationship=relationship("AuditTrail", back_populates="user")
    )
    notification_subscription: Mapped[Optional["NotificationSubscription"]] = Relationship(
        sa_relationship=relationship("NotificationSubscription", back_populates="user", cascade="all, delete-orphan", uselist=False)
    )
    notifications: Mapped[List["Notification"]] = Relationship(
        sa_relationship=relationship(
            "Notification",
            back_populates="user",
            cascade="all, delete-orphan"
        )
    )
    ai_memory: Mapped[Optional["AIMemory"]] = Relationship( # Un-commented
        sa_relationship=relationship("AIMemory", back_populates="user", cascade="all, delete-orphan", uselist=False)
    )

    model_config = { "from_attributes": True }
