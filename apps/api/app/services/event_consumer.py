# apps/api/app/services/event_consumer.py

import logging
import json
import aio_pika
from sqlmodel import select
from app.core.config import settings
from app.db.session import AsyncSessionFactory
from app import models
from app.schemas.drone import DroneEventIngest
from aio_pika.abc import AbstractIncomingMessage

logger = logging.getLogger(__name__)

async def _process_event_message(db, payload: dict):

    event_in = DroneEventIngest(**payload)
    drone_id_str = event_in.drone_id
    
    drone = (await db.execute(
        select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    )).first()
    
    if not drone:
        logger.warning(f"Received event for unknown drone: {drone_id_str}")
        return

    if event_in.event_type == models.EventType.LANDED:
        drone.status = models.DroneStatus.IDLE
        db.add(drone)
        
        if event_in.mission_id_str:
            mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
            mission = (await db.execute(mission_statement)).first()
            if mission and mission.status not in [models.MissionStatus.COMPLETED, models.MissionStatus.FAILED_EMERGENCY_LANDING]:
                final_status = models.MissionStatus.COMPLETED
                if event_in.details and event_in.details.get("reason") == "RTL":
                    final_status = models.MissionStatus.FAILED_LOW_BATTERY
                mission.status = final_status
                mission.updated_at = event_in.timestamp
                db.add(mission)

    elif event_in.event_type == models.EventType.EMERGENCY_LANDING:
        drone.status = models.DroneStatus.MAINTENANCE
        db.add(drone)
        if event_in.mission_id_str:
            mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
            mission = (await db.execute(mission_statement)).first()
            if mission:
                mission.status = models.MissionStatus.FAILED_EMERGENCY_LANDING
                mission.failure_reason = event_in.details.get("reason", "Emergency Landing Triggered") if event_in.details else "Emergency Landing Triggered"
                mission.updated_at = event_in.timestamp
                db.add(mission)

    db_event = models.DroneEvent(
        drone_id=drone.id,
        mission_id_str=event_in.mission_id_str,
        timestamp=event_in.timestamp,
        event_type=event_in.event_type,
        details=event_in.details
    )
    db.add(db_event)
    await db.commit()
    logger.info(f"Event '{db_event.event_type}' processed for drone {drone_id_str}")


def get_event_handler(app_dependencies: dict):
    async def handle_event(message: AbstractIncomingMessage):
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                payload = data.get("payload")

                if not payload:
                     logger.warning("Received event message without 'payload' field.")
                     return

                async with AsyncSessionFactory() as db:
                    await _process_event_message(db, payload)
            
            except json.JSONDecodeError:
                logger.error("Failed to decode event JSON")
            except Exception as e:
                logger.error(f"Failed to process event message: {e}", exc_info=True)

    return handle_event
