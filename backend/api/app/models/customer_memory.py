"""Consent and canonical shopping memory. Milvus is only a derived index."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def now_utc():
    return datetime.now(timezone.utc)


class CustomerMemoryConsent(SQLModel, table=True):
    __tablename__ = 'customer_memory_consent'
    user_id: int = Field(foreign_key='users.id', primary_key=True)
    enabled: bool = Field(default=False)
    policy_version: str = Field(default='shopping-v1', max_length=32)
    changed_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime(timezone=True), nullable=False))


class CustomerShoppingMemory(SQLModel, table=True):
    __tablename__ = 'customer_shopping_memory'
    __table_args__ = (UniqueConstraint('user_id','fingerprint',name='uq_customer_memory_fact'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id', index=True)
    category: str = Field(max_length=32)
    value: str = Field(max_length=120)
    fingerprint: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime(timezone=True), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
