from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import Mapped, relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .order import Order
    from .user import User


class AuditTrail(SQLModel, table=True):
    __tablename__ = "audit_trails"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    event_description: str
    changed_by: Optional[int] = Field(default=None, foreign_key="users.id")

    order: Mapped["Order"] = Relationship(
        sa_relationship=relationship("Order", back_populates="audit_trails")
    )

    user: Mapped[Optional["User"]] = Relationship(
        sa_relationship=relationship("User", back_populates="audit_changes")
    )

    model_config = {"from_attributes": True}
