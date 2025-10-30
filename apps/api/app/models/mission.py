# apps/api/app/models/mission.py

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime
from .enums import MissionStatus

if TYPE_CHECKING:
    from .order import Order
    from .drone import Drone

class Mission(SQLModel, table=True):
    __tablename__ = "missions" 
    id: Optional[int] = Field(default=None, primary_key=True)
    mission_id_str: str = Field(unique=True, index=True) 
    order_id: int = Field(foreign_key="orders.id", unique=True) 
    assigned_drone_id: Optional[int] = Field(default=None, foreign_key="drones.id")
    status: MissionStatus = Field(
        default=MissionStatus.CREATED,
        sa_column=Column(SAEnum(MissionStatus, name="missionstatus", native_enum=False), nullable=False)
    )
    waypoints_json: str 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column_kwargs={"onupdate": datetime.utcnow})
    failure_reason: Optional[str] = None

    order: Mapped["Order"] = Relationship(
        sa_relationship=relationship("Order", back_populates="mission")
    )
    assigned_drone: Mapped[Optional["Drone"]] = Relationship(
        sa_relationship=relationship("Drone", back_populates="assigned_mission")
    )

    model_config = { "from_attributes": True }
