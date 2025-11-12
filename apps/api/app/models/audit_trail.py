# apps/api/app/models/audit_trail.py 

from __future__ import annotations
from sqlmodel import SQLModel, Field, Relationship, Column
from typing import Optional, TYPE_CHECKING, Dict, Any
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy import Enum as SAEnum, JSON
from datetime import datetime
from app.models.enums import EventType

if TYPE_CHECKING:
    from .order import Order
    from .user import User
    from .drone import Drone

class AuditTrail(SQLModel, table=True):
    __tablename__ = "audit_trails"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_description: str
    changed_by: Optional[int] = Field(default=None, foreign_key="users.id")

    order: Mapped["Order"] = Relationship(
        sa_relationship=relationship("Order", back_populates="audit_trails")
    )
    user: Mapped[Optional["User"]] = Relationship(
        sa_relationship=relationship("User", back_populates="audit_changes")
    )
    
    model_config = { "from_attributes": True }

class DroneTelemetry(SQLModel, table=True):
    __tablename__ = "drone_telemetry"
    id: Optional[int] = Field(default=None, primary_key=True)
    drone_id: int = Field(foreign_key="drones.id", index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    mission_id_str: Optional[str] = Field(default=None, index=True)
    
    lat: float
    lon: float
    alt_m: float
    speed_m_s: float
    battery_pct: int
    flight_mode: Optional[str] = None

    drone: Mapped["Drone"] = Relationship(
        sa_relationship=relationship("Drone", back_populates="telemetry_logs")
    )

class DroneEvent(SQLModel, table=True):
    __tablename__ = "drone_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    drone_id: int = Field(foreign_key="drones.id", index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    mission_id_str: Optional[str] = Field(default=None, index=True)
    
    event_type: EventType = Field(
        sa_column=Column(SAEnum(EventType, name="eventtype", native_enum=False), nullable=False)
    )
    details: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON))

    drone: Mapped["Drone"] = Relationship(
        sa_relationship=relationship("Drone", back_populates="events")
    )
