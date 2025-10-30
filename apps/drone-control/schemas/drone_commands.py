# apps/drone-control/schemas/drone_commands.py

from pydantic import BaseModel, Field

class GoToPayload(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: float = Field(..., gt=0)

class DroneStatus(BaseModel):
    drone_id: str
    latitude: float
    longitude: float
    altitude: float
    battery_percent: int
    status: str 
