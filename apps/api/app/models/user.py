# apps/api/app/models/user.py

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone
from pydantic import EmailStr
from .enums import UserRole

if TYPE_CHECKING:
    from .order import Order
    from .gamification import UserBadge, UserActivity
    from .audit_trail import AuditTrail
    from .notification_subscription import NotificationSubscription
    from .notification import Notification
    from .aimemory import AIMemory

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = Field(default=None, index=True) # Indexed for admin search
    email: EmailStr = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False) # Security Standard

    role: UserRole = Field(
        default=UserRole.USER, # تأكد إن دي القيمة الافتراضية المناسبة ليك
        sa_column=Column(
            SAEnum(UserRole, name="userrole", native_enum=False), 
            nullable=False,
            index=True  # 👈 التصحيح: نقلنا الفهرس هنا
        )
    )
    
    # Diamond Standard: UTC Timezones + Update Tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    last_login: Optional[datetime] = Field(default=None)

    phone_number: Optional[str] = Field(default=None, index=True, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    city: Optional[str] = Field(default=None, nullable=True)
    country: Optional[str] = Field(default=None, nullable=True)
    avatar_url: Optional[str] = Field(default=None, nullable=True)

    stripe_customer_id: Optional[str] = Field(default=None, index=True, nullable=True)

    # --- Relationships ---
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
    ai_memory: Mapped[Optional["AIMemory"]] = Relationship(
        sa_relationship=relationship("AIMemory", back_populates="user", cascade="all, delete-orphan", uselist=False)
    )
    activities: Mapped[List["UserActivity"]] = Relationship(
        sa_relationship=relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    )

    model_config = { "from_attributes": True }
