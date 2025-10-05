from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from .order import Order
    from .gamification import UserBadge
    from .audit_trail import AuditTrail
    from .notification_subscription import NotificationSubscription

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

    orders: Mapped[List["Order"]] = Relationship(back_populates="user")
    badges: Mapped[List["UserBadge"]] = Relationship(back_populates="user")
    audit_changes: Mapped[List["AuditTrail"]] = Relationship(back_populates="user")
    notification_subscription: Mapped[Optional["NotificationSubscription"]] = Relationship(back_populates="user")

    model_config = { "from_attributes": True }
