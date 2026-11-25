# backend/api/app/schemas/audit_trail.py

from sqlmodel import SQLModel
from datetime import datetime

class AuditTrailBase(SQLModel):
    action: str
    details: str | None = None

class AuditTrailCreate(AuditTrailBase):
    order_id: int
    user_id: int

class AuditTrail(AuditTrailBase):
    id: int
    order_id: int
    user_id: int
    timestamp: datetime

    model_config = {
        "from_attributes": True
    }
