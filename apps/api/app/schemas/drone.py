# apps/api/app/schemas/drone.py

from __future__ import annotations
from typing import Optional, Any, Dict 
from sqlmodel import SQLModel
from datetime import datetime
from app.models.drone import DroneStatus
from app.models.enums import EventType

class DroneBase(SQLModel):
    model: str
    battery_level: int = 100
    status: DroneStatus = DroneStatus.IDLE

class DroneCreate(DroneBase):
    pass

class DroneUpdate(DroneBase):
    pass

class DroneInDBBase(DroneBase):
    id: int
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None

    model_config = {
        "from_attributes": True
    }

class Drone(DroneInDBBase): 
    pass

class DroneTelemetryCreate(SQLModel):
    mission_id_str: Optional[str] = None
    timestamp: datetime
    lat: float
    lon: float
    alt_m: float
    speed_m_s: float
    battery_pct: int
    flight_mode: Optional[str] = None
    raw_payload_json: Optional[str | Dict[str, Any]] = None 

class DroneEventCreate(SQLModel):
    mission_id_str: Optional[str] = None
    timestamp: datetime
    event_type: EventType 
    details: Optional[Dict[str, Any]] = None
