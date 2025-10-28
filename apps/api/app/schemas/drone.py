# file: airdeliver/apps/api/app/schemas/drone.py (Fixed)

from __future__ import annotations
from typing import Optional, Any, Dict # <-- 💡 تم إضافة Any, Dict
from sqlmodel import SQLModel
from datetime import datetime # <-- 💡 تم إضافة datetime

from app.models.drone import DroneStatus
from app.models.enums import EventType # <-- 💡 تم إضافة EventType

# Shared properties
class DroneBase(SQLModel):
    model: str
    battery_level: int = 100
    status: DroneStatus = DroneStatus.IDLE


# Properties to receive on drone creation
class DroneCreate(DroneBase):
    pass


# Properties to receive on drone update
class DroneUpdate(DroneBase):
    pass


# Properties shared by models stored in DB
class DroneInDBBase(DroneBase):
    id: int
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None

    # Correct configuration for Pydantic v2
    model_config = {
        "from_attributes": True
    }


# Properties to return to client
class Drone(DroneInDBBase): # <-- 💡 هذا هو الكلاس الذي يجب استخدامه كـ 'DroneRead'
    pass

# --- 💡 تمت إضافة الـ Schemas المفقودة هنا ---

# Schema for receiving telemetry data from WebSocket server
class DroneTelemetryCreate(SQLModel):
    mission_id_str: Optional[str] = None
    timestamp: datetime
    lat: float
    lon: float
    alt_m: float
    speed_m_s: float
    battery_pct: int
    flight_mode: Optional[str] = None
    raw_payload_json: Optional[str | Dict[str, Any]] = None # Allow string or JSON

# Schema for receiving event data from WebSocket server
class DroneEventCreate(SQLModel):
    mission_id_str: Optional[str] = None
    timestamp: datetime
    event_type: EventType # Use the enum
    details: Optional[Dict[str, Any]] = None
