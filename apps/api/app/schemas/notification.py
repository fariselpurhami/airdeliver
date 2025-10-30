# apps/api/app/schemas/notification.py 

from sqlmodel import SQLModel
from datetime import datetime
from app.models.enums import NotificationType

class NotificationRead(SQLModel):
    id: int
    title: str
    body: str
    type: NotificationType
    read: bool
    cta: str | None
    created_at: datetime
    timestamp: str 

class NotificationCreate(SQLModel):
    user_id: int
    title: str
    body: str
    type: NotificationType = NotificationType.SYSTEM_ALERT
    cta: str | None = None
    meta: dict | None = None
