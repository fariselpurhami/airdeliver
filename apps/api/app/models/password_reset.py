"""Durable single-use reset credentials. Never store raw reset tokens."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

class PasswordResetToken(SQLModel, table=True):
    __tablename__ = 'password_reset_tokens'
    token_hash: str = Field(primary_key=True, max_length=64)
    user_id: int = Field(foreign_key='users.id', index=True)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))

class PasswordResetAudit(SQLModel, table=True):
    __tablename__ = 'password_reset_audits'
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key='users.id', index=True)
    event: str = Field(max_length=40)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))

class PasswordResetAdmission(SQLModel, table=True):
    __tablename__ = 'password_reset_admission'
    key_hash: str = Field(primary_key=True, max_length=64)
    window: int
    count: int = 1

class PasswordResetDelivery(SQLModel, table=True):
    __tablename__ = 'password_reset_deliveries'
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='users.id', index=True)
    encrypted_payload: str
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    sent_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    attempts: int = 0
