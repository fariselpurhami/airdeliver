# backend/api/app/models/gamification.py

from __future__ import annotations
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .user import User

class UserActivity(SQLModel, table=True):
    __tablename__ = "user_activities"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    activity_type: str = Field(index=True) 
    points_awarded: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))

    user: Mapped["User"] = Relationship(
        sa_relationship=relationship("User", back_populates="activities")
    )

class Badge(SQLModel, table=True):
    __tablename__ = "badges"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str
    icon_url: str

    user_badges: Mapped[List["UserBadge"]] = Relationship(sa_relationship=relationship("UserBadge", back_populates="badge"))

    model_config = { "from_attributes": True }

class UserBadge(SQLModel, table=True):
    __tablename__ = "user_badges"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    badge_id: int = Field(foreign_key="badges.id", primary_key=True)
    awarded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))

    user: Mapped["User"] = Relationship(sa_relationship=relationship("User", back_populates="badges"))
    badge: Mapped["Badge"] = Relationship(sa_relationship=relationship("Badge", back_populates="user_badges"))

    model_config = { "from_attributes": True }
