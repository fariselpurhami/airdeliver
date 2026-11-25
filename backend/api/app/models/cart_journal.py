"""Prepared canonical cart state and operation journal, not traffic-enabled."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, JSON, UniqueConstraint
from sqlmodel import SQLModel, Field


class CustomerCartState(SQLModel, table=True):
    __tablename__ = 'customer_cart_state'
    user_id: int = Field(foreign_key='users.id', primary_key=True)
    revision: int = Field(default=0)
    state: dict = Field(default_factory=lambda: {'items': [], 'total': '0.00'}, sa_column=Column(JSON, nullable=False))
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))


class CartMutationRecord(SQLModel, table=True):
    __tablename__ = 'cart_mutation_record'
    __table_args__ = (UniqueConstraint('user_id', 'mutation_id', name='uq_cart_mutation_customer_key'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id', index=True)
    mutation_id: str = Field(max_length=36)
    fingerprint: str = Field(max_length=64)
    revision: int
    outcome: dict = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
