# apps/api/app/api/v1/endpoints/commands.py

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import json
import logging
from app import models
from app.schemas.drone import CommandStartMission, CommandWrapper
from app.services.rabbitmq_service import rabbitmq_service
from app.core.config import settings
from app.api import deps

router = APIRouter()


async def get_drone_by_id_str(
    drone_id_str: str, session: AsyncSession
) -> models.Drone:
    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = (await session.exec(statement)).first()
    if not drone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone {drone_id_str} not found"
        )
    return drone


@router.post("/{drone_id_str}/start_mission", status_code=status.HTTP_202_ACCEPTED)
async def command_start_mission(
    *,
    session: AsyncSession = Depends(deps.get_session),
    drone_id_str: str,
    mission_payload: CommandStartMission,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    drone = await get_drone_by_id_str(drone_id_str, session)

    if drone.status not in [models.DroneStatus.IDLE, models.DroneStatus.OFFLINE]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Drone {drone_id_str} is not IDLE (current: {drone.status}). Cannot start mission.",
        )

    command = CommandWrapper(command="start_mission", payload=mission_payload.model_dump())

    routing_key = f"drone.{drone.drone_id_str}"
    message_body = command.model_dump_json().encode()

    try:
        await rabbitmq_service.publish_command(routing_key, message_body)
        logging.info(
            f"Published start_mission command for {drone_id_str} to {routing_key}"
        )
        return {"message": "Mission command queued for drone."}
    except Exception as e:
        logging.error(f"Failed to publish command to RabbitMQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue command.",
        )


@router.post("/{drone_id_str}/return_to_home", status_code=status.HTTP_202_ACCEPTED)
async def command_return_to_home(
    *,
    session: AsyncSession = Depends(deps.get_session),
    drone_id_str: str,
    current_user: models.User = Depends(deps.get_current_admin_user),
):
    drone = await get_drone_by_id_str(drone_id_str, session)

    if drone.status not in [models.DroneStatus.IN_MISSION, models.DroneStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Drone {drone_id_str} is not IN_MISSION or PAUSED (current: {drone.status}).",
        )

    command = CommandWrapper(command="return_to_home", payload={})

    routing_key = f"drone.{drone.drone_id_str}"
    message_body = command.model_dump_json().encode()

    try:
        await rabbitmq_service.publish_command(routing_key, message_body)
        logging.info(
            f"Published return_to_home command for {drone_id_str} to {routing_key}"
        )
        return {"message": "RTL command queued for drone."}
    except Exception as e:
        logging.error(f"Failed to publish command to RabbitMQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue command.",
        )
