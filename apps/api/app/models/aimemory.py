# file: airdeliver/apps/api/app/models/aimemory.py

from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime

if TYPE_CHECKING:
    from .user import User

class AIMemory(SQLModel, table=True):
    __tablename__ = "ai_memory" # Added table name
    id: Optional[int] = Field(default=None, primary_key=True) # Changed type hint
    user_id: int = Field(foreign_key="users.id", unique=True)

    context_data: Dict[str, Any] = Field(sa_column=Column(JSON))
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    user: Mapped["User"] = Relationship(sa_relationship=relationship("User", back_populates="ai_memory"))

    model_config = { "from_attributes": True }
