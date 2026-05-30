# apps/api/app/models/mission.py

from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Dict, Any, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime, timezone
from .enums import MissionStatus

if TYPE_CHECKING:
    from .order import Order
class Mission(SQLModel, table=True):
    __tablename__ = "missions" 
    id: Optional[int] = Field(default=None, primary_key=True)
    mission_id_str: str = Field(unique=True, index=True) 
    order_id: int = Field(foreign_key="orders.id", unique=True)   

    status: MissionStatus = Field(
        default=MissionStatus.CREATED,
        sa_column=Column(
            SAEnum(MissionStatus, name="missionstatus", native_enum=False),
            nullable=False,
            index=True  # 👈 التصحيح: نقلنا الفهرس هنا
        )
    )
    
    # HARDENING FIX: Storing waypoints as JSON, not String, for queryability and correctness
    waypoints: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    failure_reason: Optional[str] = None

    order: Mapped["Order"] = Relationship(
        sa_relationship=relationship("Order", back_populates="mission")
    )

    model_config = { "from_attributes": True }
