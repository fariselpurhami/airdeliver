from __future__ import annotations
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .order import Order
    from .user import User

class AuditTrail(SQLModel, table=True):
    __tablename__ = "audit_trails"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_description: str
    changed_by: Optional[int] = Field(default=None, foreign_key="users.id")

    order: Mapped["Order"] = Relationship(back_populates="audit_trails")
    user: Mapped[Optional["User"]] = Relationship(back_populates="audit_changes")
    
    model_config = { "from_attributes": True }
