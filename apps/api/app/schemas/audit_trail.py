# In airdeliver/apps/api/app/schemas/audit_trail.py

from sqlmodel import SQLModel
from datetime import datetime

# Shared properties
class AuditTrailBase(SQLModel):
    action: str
    details: str | None = None

# Properties to receive on creation
class AuditTrailCreate(AuditTrailBase):
    order_id: int
    user_id: int

# Properties to return to client
class AuditTrail(AuditTrailBase):
    id: int
    order_id: int
    user_id: int
    timestamp: datetime

    # Correct configuration for Pydantic v2
    model_config = {
        "from_attributes": True
    }
