# apps/api/app/services/telemetry_consumer.py

import json
import logging
from aio_pika.abc import AbstractIncomingMessage
from app.db.session import AsyncSessionFactory
from app import models
from app.schemas.drone import DroneTelemetryIngest
from sqlmodel import select

logger = logging.getLogger(__name__)

async def _process_telemetry_message(db, payload: dict):
    
    telemetry_in = DroneTelemetryIngest(**payload)
    drone_id_str = telemetry_in.drone_id
    
    drone = (await db.execute(
        select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    )).first()
    
    if not drone:
        logger.warning(f"Skipping telemetry: Drone {drone_id_str} not found in DB")
        return

    db_telemetry = models.DroneTelemetry(
        drone_id=drone.id,
        mission_id_str=telemetry_in.mission_id_str,
        timestamp=telemetry_in.timestamp,
        lat=telemetry_in.lat,
        lon=telemetry_in.lon,
        alt_m=telemetry_in.alt_m,
        speed_m_s=telemetry_in.ground_speed_m_s,
        battery_pct=telemetry_in.battery_pct,
        flight_mode=telemetry_in.flight_mode,
    )
    db.add(db_telemetry)

    drone.current_lat = telemetry_in.lat
    drone.current_lon = telemetry_in.lon
    drone.current_battery_pct = telemetry_in.battery_pct
    drone.last_seen = telemetry_in.timestamp

    if telemetry_in.flight_mode in ["AUTO", "MISSION", "OFFBOARD"] and drone.status != models.DroneStatus.IN_MISSION:
        drone.status = models.DroneStatus.IN_MISSION
    elif telemetry_in.flight_mode == "RTL" and drone.status != models.DroneStatus.RETURNING:
        drone.status = models.DroneStatus.RETURNING
    elif telemetry_in.flight_mode == "LAND" and drone.status != models.DroneStatus.LANDING:
        drone.status = models.DroneStatus.LANDING
    
    session.add(drone)
    await db.commit()
    logger.debug(f"Telemetry processed for drone {drone_id_str}")


def get_telemetry_handler(app_dependencies: dict):
    async def handle_telemetry(message: AbstractIncomingMessage):
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                payload = data.get("payload")
                
                if not payload:
                     logger.warning("Received telemetry message without 'payload' field.")
                     return

                async with AsyncSessionFactory() as db:
                    await _process_telemetry_message(db, payload)
            except json.JSONDecodeError:
                logger.error("Failed to decode telemetry JSON")
            except Exception as e:
                logger.error(f"Error processing telemetry message: {e}", exc_info=True)

    return handle_telemetry
