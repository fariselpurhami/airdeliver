# apps/api/app/schemas/drone.py

from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import DroneStatus, EventType
from app.models.drone import Drone as DroneModel

class DroneBase(SQLModel):
    drone_id_str: str = Field(unique=True, index=True) 
    model: Optional[str] = None
    home_base_lat: Optional[float] = None
    home_base_lon: Optional[float] = None
    meta: Optional[Dict[str, Any]] = Field(default={})

class DroneCreate(DroneBase):
    pass

class DroneRead(DroneBase):
    id: int
    status: DroneStatus
    current_battery_pct: Optional[int]
    last_seen: Optional[datetime]
    current_lat: Optional[float]
    current_lon: Optional[float]

class DroneUpdate(SQLModel):
    model: Optional[str] = None
    home_base_lat: Optional[float] = None
    home_base_lon: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

class DroneTelemetryIngest(BaseModel):
    drone_id: str
    timestamp: datetime
    mission_id_str: Optional[str] = None
    lat: float
    lon: float
    alt_m: float
    ground_speed_m_s: float
    battery_pct: int
    flight_mode: str

class DroneEventIngest(BaseModel):
    drone_id: str
    timestamp: datetime
    event_type: EventType
    mission_id_str: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class CommandWaypoint(BaseModel):
    lat: float
    lon: float
    alt_m: float

class CommandStartMission(BaseModel):
    mission_id: str
    waypoints: List[CommandWaypoint]
    
class CommandWrapper(BaseModel):
    command: str
    payload: Dict[str, Any]
