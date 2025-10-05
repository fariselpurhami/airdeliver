# In airdeliver/apps/api/app/schemas/drone.py

from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel

from app.models.drone import DroneStatus


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
class Drone(DroneInDBBase):
    pass
