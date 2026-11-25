"""Durable, at-least-once publication of committed payment domain events."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class PaymentOutbox(SQLModel, table=True):
    __tablename__ = "payment_outbox"
    __table_args__ = (UniqueConstraint("order_id", "kind", name="uq_payment_outbox_order_kind"),)
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=36)
    order_id: int = Field(foreign_key="orders.id", index=True)
    kind: str = Field(max_length=64)
    routing_key: str = Field(max_length=128)
    payload: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    attempts: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    next_attempt_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    delivered_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True, index=True))
    last_error: Optional[str] = Field(default=None, max_length=128)
