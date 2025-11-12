# apps/api/app/services/telemetry_consumer.py

import logging
import json
import aio_pika
from sqlmodel import select
from app.core.config import settings
from app.db.session import get_session
from app import models
from app.schemas.drone import DroneTelemetryIngest

async def process_telemetry_message(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            telemetry_in = DroneTelemetryIngest(**data["payload"])
            drone_id_str = telemetry_in.drone_id
            
            async with get_session() as session:
                statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
                drone = (await session.exec(statement)).first()
                if not drone:
                    logging.error(f"Received telemetry for unknown drone: {drone_id_str}")
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
                session.add(db_telemetry)

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
                await session.commit()

        except json.JSONDecodeError:
            logging.error("Failed to decode telemetry JSON")
        except Exception as e:
            logging.error(f"Failed to process telemetry message: {e}")

async def consume_telemetry(connection_pool):
    logging.info("Starting Telemetry Consumer...")
    async with connection_pool.acquire() as connection:
        channel = await connection.channel()
        queue = await channel.get_queue(settings.QUEUE_TELEMETRY)
        await queue.bind(settings.EXCHANGE_TELEMETRY, routing_key="drone.*")
        await queue.consume(process_telemetry_message)
        logging.info("Telemetry Consumer is consuming.")
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            logging.info("Telemetry Consumer stopped.")
