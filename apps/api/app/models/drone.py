# apps/api/app/models/drone.py

# 1. قم بتعديل سطر الاستيراد هذا
from sqlmodel import SQLModel, Field, Column, Relationship, JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from .enums import DroneStatus

if TYPE_CHECKING:
    from .mission import Mission
    from .audit_trail import DroneTelemetry, DroneEvent
    from .order import Order 

class Drone(SQLModel, table=True):
    __tablename__ = "drones"
    id: Optional[int] = Field(default=None, primary_key=True)
    drone_id_str: str = Field(unique=True, index=True) 
    model: Optional[str] = None
    home_base_lat: Optional[float] = None
    home_base_lon: Optional[float] = None
    
    meta: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON))
    
    status: DroneStatus = Field(
        default=DroneStatus.OFFLINE,
        sa_column=Column(SAEnum(DroneStatus, name="dronestatus", native_enum=False), nullable=False)
    )
    current_battery_pct: Optional[int] = Field(default=None, ge=0, le=100)
    last_seen: Optional[datetime] = Field(default=None)
    current_lat: Optional[float] = Field(default=None)
    current_lon: Optional[float] = Field(default=None)

    missions: Mapped[List["Mission"]] = Relationship(
        sa_relationship=relationship("Mission", back_populates="assigned_drone")
    )


    assigned_orders: Mapped[List["Order"]] = Relationship(
        sa_relationship=relationship("Order", back_populates="drone")
    )
    
    telemetry_logs: Mapped[List["DroneTelemetry"]] = Relationship(
        sa_relationship=relationship(
            "DroneTelemetry", 
            back_populates="drone", 
            cascade="all, delete-orphan"
        )
    )
    
    events: Mapped[List["DroneEvent"]] = Relationship(
        sa_relationship=relationship(
            "DroneEvent", 
            back_populates="drone", 
            cascade="all, delete-orphan"
        )
    )
