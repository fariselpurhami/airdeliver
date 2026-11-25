# backend/api/app/models/aimemory.py

from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, DateTime
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .user import User

class AIMemory(SQLModel, table=True):
    __tablename__ = "ai_memory" 
    id: Optional[int] = Field(default=None, primary_key=True) 
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)

    context_data: Dict[str, Any] = Field(sa_column=Column(JSON))
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc))
    )

    user: Mapped["User"] = Relationship(sa_relationship=relationship("User", back_populates="ai_memory"))

    model_config = { "from_attributes": True }
