from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from enum import Enum
from pydantic import field_validator

if TYPE_CHECKING:
    from .order import Order

class DroneStatus(str, Enum):
    IDLE = "idle"
    CHARGING = "charging"
    DELIVERING = "delivering"
    RETURNING = "returning"
    MAINTENANCE = "maintenance"

class Drone(SQLModel, table=True):
    __tablename__ = "drones"
    id: Optional[int] = Field(default=None, primary_key=True)
    model: str
    battery_level: int = Field(default=100)
    current_lat: Optional[float] = Field(default=None)
    current_lon: Optional[float] = Field(default=None)
    status: DroneStatus = Field(
        default=DroneStatus.IDLE,
        sa_column=Column(SAEnum(DroneStatus, name="dronestatus", native_enum=False), nullable=False)
    )

    assigned_orders: Mapped[List["Order"]] = Relationship(sa_relationship=relationship("Order", back_populates="drone"))

    @field_validator('battery_level')
    @classmethod
    def validate_battery_level(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError('Battery level must be between 0 and 100')
        return v

    model_config = { "from_attributes": True }
