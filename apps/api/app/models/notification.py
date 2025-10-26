# file: apps/api/app/models/notification.py
# --- النسخة المصححة ---

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from enum import Enum
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
# 1. سنستخدم Mapped فقط للعلاقات، لذا سنستوردها
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from .user import User

class NotificationType(str, Enum):
    order = "order"
    security = "security"
    promotion = "promotion"
    system = "system"
    default = "default"

class NotificationBase(SQLModel):
    # --- 2. التصحيح: إزالة Mapped من الحقول العادية ---
    title: str = Field(index=True)
    body: str
    
    # هذا الأسلوب صحيح ومتطابق مع user.py
    type: NotificationType = Field(
        default=NotificationType.default,
        sa_column=Column(
            SAEnum(NotificationType, name="notification_type_enum", native_enum=False), 
            nullable=False
        )
    )
    
    read: bool = Field(default=False)
    cta: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"
    
    id: Optional[int] = Field(default=None, primary_key=True) # <-- استخدم Optional[int] للـ PKs
    
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    
    # --- 3. هنا فقط نستخدم Mapped ---
    # هذا هو الأسلوب الصحيح للعلاقات (ليطابق user.py)
    user: Mapped["User"] = Relationship(
        sa_relationship=relationship("User", back_populates="notifications")
    )

    meta: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
