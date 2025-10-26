from sqlmodel import SQLModel
from datetime import datetime
from app.models.notification import NotificationType # Import the Enum from the model file

# Schema for reading a notification
class NotificationRead(SQLModel):
    id: int
    title: str
    body: str
    type: NotificationType
    read: bool
    cta: str | None
    created_at: datetime
    # timestamp (for frontend)
    timestamp: str # We will format this in the endpoint

# Schema for creating (used internally by the system)
class NotificationCreate(SQLModel):
    user_id: int
    title: str
    body: str
    type: NotificationType = NotificationType.default
    cta: str | None = None
    meta: dict | None = None
