from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from .user import User

class NotificationSubscription(SQLModel, table=True):
    __tablename__ = "notification_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    subscription_info_json: dict = Field(sa_column=Column(JSON))

    user: Mapped["User"] = Relationship(sa_relationship=relationship("User", back_populates="notification_subscription"))

    model_config = { "from_attributes": True }
