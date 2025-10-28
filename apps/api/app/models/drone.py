# file: airdeliver/apps/api/app/models/drone.py (Corrected)

from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime
from pydantic import field_validator # Import validator

# Import Enums from the dedicated file
from .enums import DroneStatus, EventType

# Forward references
if TYPE_CHECKING:
    from .order import Order
    from .mission import Mission

class Drone(SQLModel, table=True):
    __tablename__ = "drones"
    id: Optional[int] = Field(default=None, primary_key=True)
    drone_id_str: str = Field(unique=True, index=True) # Public ID
    model: Optional[str] = None
    status: DroneStatus = Field(
        default=DroneStatus.OFFLINE,
        sa_column=Column(SAEnum(DroneStatus, name="dronestatus", native_enum=False), nullable=False)
    )
    current_battery_pct: Optional[int] = Field(default=100, ge=0, le=100)
    last_seen: Optional[datetime] = None
    current_lat: Optional[float] = Field(default=None)
    current_lon: Optional[float] = Field(default=None)
    home_base_lat: Optional[float] = None
    home_base_lon: Optional[float] = None
    meta: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    assigned_orders: Mapped[List["Order"]] = Relationship( # Direct link from Drone to Order
        sa_relationship=relationship("Order", back_populates="drone")
    )
    assigned_mission: Mapped[Optional["Mission"]] = Relationship(
        sa_relationship=relationship("Mission", back_populates="assigned_drone")
    )
    telemetry_logs: Mapped[List["DroneTelemetry"]] = Relationship(
        sa_relationship=relationship("DroneTelemetry", back_populates="drone", cascade="all, delete-orphan")
    )
    events: Mapped[List["DroneEvent"]] = Relationship(
        sa_relationship=relationship("DroneEvent", back_populates="drone", cascade="all, delete-orphan")
    )

    # Corrected validator name
    @field_validator('current_battery_pct')
    @classmethod
    def validate_battery_level(cls, v: Optional[int]) -> Optional[int]: # Made Optional to match field
        if v is not None and not 0 <= v <= 100:
            raise ValueError('Battery level must be between 0 and 100')
        return v

    model_config = { "from_attributes": True }

# Model for Telemetry Logs
class DroneTelemetry(SQLModel, table=True):
    __tablename__ = "drone_telemetry"
    id: Optional[int] = Field(default=None, primary_key=True)
    drone_id: int = Field(foreign_key="drones.id", index=True)
    mission_id_str: Optional[str] = Field(default=None, index=True)
    timestamp: datetime = Field(index=True, default_factory=datetime.utcnow)
    lat: float
    lon: float
    alt_m: float
    speed_m_s: float
    battery_pct: int
    flight_mode: Optional[str] = None
    raw_payload_json: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON))

    drone: Mapped["Drone"] = Relationship(
        sa_relationship=relationship("Drone", back_populates="telemetry_logs")
    )

    model_config = { "from_attributes": True }

# Model for Drone Events
class DroneEvent(SQLModel, table=True):
    __tablename__ = "drone_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    drone_id: int = Field(foreign_key="drones.id", index=True)
    mission_id_str: Optional[str] = Field(default=None, index=True)
    timestamp: datetime = Field(index=True, default_factory=datetime.utcnow)
    event_type: EventType = Field(
         sa_column=Column(SAEnum(EventType, name="eventtype", native_enum=False), nullable=False)
    )
    details: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON))

    drone: Mapped["Drone"] = Relationship(
        sa_relationship=relationship("Drone", back_populates="events")
    )

    model_config = { "from_attributes": True }
