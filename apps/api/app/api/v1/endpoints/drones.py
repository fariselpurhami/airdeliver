# apps/api/app/api/v1/endpoints/drones.py 

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session, select
from typing import List, Optional, Any
from datetime import datetime
import logging 
from app import models
from app.schemas.drone import ( Drone as DroneRead, DroneCreate, DroneUpdate, DroneTelemetryCreate, DroneEventCreate)
from app.db.session import get_session
from app.api import deps 

router = APIRouter()

@router.post("/", response_model=DroneRead, status_code=status.HTTP_201_CREATED)
def create_drone(
    *,
    session: Session = Depends(get_session),
    drone_in: DroneCreate,
):

    db_drone = models.Drone.model_validate(drone_in) 
    session.add(db_drone)
    session.commit()
    session.refresh(db_drone)
    return db_drone

@router.get("/", response_model=List[DroneRead])
def read_drones(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):

    statement = select(models.Drone).offset(skip).limit(limit)
    drones = session.exec(statement).all()
    return drones

@router.get("/{drone_id_str}", response_model=DroneRead)
def read_drone(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str,
):

    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = session.exec(statement).first()
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    return drone

@router.put("/{drone_id_str}", response_model=DroneRead)
def update_drone(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str,
    drone_in: DroneUpdate, 
):

    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    db_drone = session.exec(statement).first()
    if not db_drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")

    update_data = drone_in.model_dump(exclude_unset=True)
    db_drone.sqlmodel_update(update_data)
    session.add(db_drone)
    session.commit()
    session.refresh(db_drone)
    return db_drone

@router.post("/{drone_id_str}/telemetry", status_code=status.HTTP_201_CREATED)
def record_telemetry(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str,
    telemetry_in: DroneTelemetryCreate, 
):

    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = session.exec(statement).first()
    if not drone:
        logging.error(f"Received telemetry for unknown drone ID string: {drone_id_str}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone with ID {drone_id_str} not found")

    db_telemetry = models.DroneTelemetry(
        drone_id=drone.id,
        mission_id_str=telemetry_in.mission_id_str,
        timestamp=telemetry_in.timestamp, 
        lat=telemetry_in.lat,
        lon=telemetry_in.lon,
        alt_m=telemetry_in.alt_m,
        speed_m_s=telemetry_in.speed_m_s,
        battery_pct=telemetry_in.battery_pct,
        flight_mode=telemetry_in.flight_mode,
        raw_payload_json=telemetry_in.raw_payload_json if isinstance(telemetry_in.raw_payload_json, str) else str(telemetry_in.raw_payload_json)
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

    session.commit()

    return {"status": "Telemetry recorded"}


@router.post("/{drone_id_str}/events", status_code=status.HTTP_201_CREATED)
def record_event(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str,
    event_in: DroneEventCreate, 
):

    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = session.exec(statement).first()
    if not drone:
        logging.error(f"Received event for unknown drone ID string: {drone_id_str}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone with ID {drone_id_str} not found")

    if event_in.event_type == models.EventType.LANDED:
         drone.status = models.DroneStatus.IDLE 
         session.add(drone)
         
         if event_in.mission_id_str:
             mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
             mission = session.exec(mission_statement).first()
             if mission and mission.status not in [models.MissionStatus.COMPLETED, models.MissionStatus.FAILED_EMERGENCY_LANDING]: 
                  final_status = models.MissionStatus.COMPLETED 
                  if event_in.details and "reason" in event_in.details:
                      if event_in.details["reason"] == "RTL": final_status = models.MissionStatus.FAILED_LOW_BATTERY 
                  mission.status = final_status
                  mission.updated_at = event_in.timestamp
                  session.add(mission)

    elif event_in.event_type == models.EventType.EMERGENCY_LANDING:
         drone.status = models.DroneStatus.MAINTENANCE 
         session.add(drone)
         if event_in.mission_id_str:
              mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
              mission = session.exec(mission_statement).first()
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
    session.commit()
    return {"status": "Event recorded"}
