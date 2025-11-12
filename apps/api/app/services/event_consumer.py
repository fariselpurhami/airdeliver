# apps/api/app/services/event_consumer.py

import logging
import json
import aio_pika
from sqlmodel import select
from app.core.config import settings
from app.db.session import get_session
from app import models
from app.schemas.drone import DroneEventIngest

async def process_event_message(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        try:
            data = json.loads(message.body.decode())
            event_in = DroneEventIngest(**data["payload"])
            drone_id_str = event_in.drone_id
            
            async with get_session() as session:
                statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
                drone = (await session.exec(statement)).first()
                if not drone:
                    logging.error(f"Received event for unknown drone: {drone_id_str}")
                    return

                if event_in.event_type == models.EventType.LANDED:
                    drone.status = models.DroneStatus.IDLE
                    session.add(drone)
                    
                    if event_in.mission_id_str:
                        mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
                        mission = (await session.exec(mission_statement)).first()
                        if mission and mission.status not in [models.MissionStatus.COMPLETED, models.MissionStatus.FAILED_EMERGENCY_LANDING]:
                            final_status = models.MissionStatus.COMPLETED
                            if event_in.details and event_in.details.get("reason") == "RTL":
                                final_status = models.MissionStatus.FAILED_LOW_BATTERY
                            mission.status = final_status
                            mission.updated_at = event_in.timestamp
                            session.add(mission)

                elif event_in.event_type == models.EventType.EMERGENCY_LANDING:
                    drone.status = models.DroneStatus.MAINTENANCE
                    session.add(drone)
                    if event_in.mission_id_str:
                        mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
                        mission = (await session.exec(mission_statement)).first()
                        if mission:
                            mission.status = models.MissionStatus.FAILED_EMERGENCY_LANDING
                            mission.failure_reason = event_in.details.get("reason", "Emergency Landing Triggered") if event_in.details else "Emergency Landing Triggered"
                            mission.updated_at = event_in.timestamp
                            session.add(mission)

                db_event = models.DroneEvent(
                    drone_id=drone.id,
                    mission_id_str=event_in.mission_id_str,
                    timestamp=event_in.timestamp,
                    event_type=event_in.event_type,
                    details=event_in.details
                )
                session.add(db_event)
                await session.commit()
        
        except json.JSONDecodeError:
            logging.error("Failed to decode event JSON")
        except Exception as e:
            logging.error(f"Failed to process event message: {e}")

async def consume_events(connection_pool):
    logging.info("Starting Event Consumer...")
    async with connection_pool.acquire() as connection:
        channel = await connection.channel()
        queue = await channel.get_queue(settings.QUEUE_EVENTS)
        await queue.bind(settings.EXCHANGE_EVENTS, routing_key="drone.*")
        await queue.consume(process_event_message)
        logging.info("Event Consumer is consuming.")
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            logging.info("Event Consumer stopped.")
