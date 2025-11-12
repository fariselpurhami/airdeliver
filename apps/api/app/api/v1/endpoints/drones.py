# apps/api/app/api/v1/endpoints/drones.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
from app import models
from app.schemas.drone import DroneRead, DroneCreate, DroneUpdate
from app.db.session import get_session
from app.api import deps


router = APIRouter()


@router.post("/", response_model=DroneRead, status_code=status.HTTP_201_CREATED)
async def create_drone(
    *,
    session: AsyncSession = Depends(get_session),
    drone_in: DroneCreate,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    db_drone = models.Drone.model_validate(drone_in)
    session.add(db_drone)
    await session.commit()
    await session.refresh(db_drone)
    return db_drone


@router.get("/", response_model=List[DroneRead])
async def read_drones(
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):
    statement = select(models.Drone).offset(skip).limit(limit)
    drones = (await session.exec(statement)).all()
    return drones


@router.get("/{drone_id_str}", response_model=DroneRead)
async def read_drone(
    *,
    session: AsyncSession = Depends(get_session),
    drone_id_str: str,
):
    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = (await session.exec(statement)).first()
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    return drone


@router.put("/{drone_id_str}", response_model=DroneRead)
async def update_drone(
    *,
    session: AsyncSession = Depends(get_session),
    drone_id_str: str,
    drone_in: DroneUpdate,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    db_drone = (await session.exec(statement)).first()
    if not db_drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")

    update_data = drone_in.model_dump(exclude_unset=True)
    db_drone.sqlmodel_update(update_data)
    session.add(db_drone)
    await session.commit()
    await session.refresh(db_drone)
    return db_drone
