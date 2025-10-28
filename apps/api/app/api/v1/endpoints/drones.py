# file: airdeliver/apps/api/app/api/v1/endpoints/drones.py (Fixed)

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session, select
from typing import List, Optional, Any
from datetime import datetime
import logging # <-- 💡 1. تم إضافة استيراد logging

# Import models and schemas
from app import models
# --- 💡 2. تم إصلاح سطر الاستيراد بالكامل ---
from app.schemas.drone import (
    Drone as DroneRead,  # استيراد 'Drone' وتسميته 'DroneRead'
    DroneCreate, 
    DroneUpdate, 
    DroneTelemetryCreate, 
    DroneEventCreate
)
from app.db.session import get_session
from app.api import deps # For potential authentication/authorization

router = APIRouter()

# --- CRUD for Drones (Example - Admin/Operator only) ---

@router.post("/", response_model=DroneRead, status_code=status.HTTP_201_CREATED)
def create_drone(
    *,
    session: Session = Depends(get_session),
    drone_in: DroneCreate, # This now exists
    # current_user: models.User = Depends(deps.get_current_active_admin), # Protect this endpoint
):
    """
    Register a new drone in the system. (Admin/Operator)
    """
    db_drone = models.Drone.model_validate(drone_in) # Use model_validate for Pydantic v2
    session.add(db_drone)
    session.commit()
    session.refresh(db_drone)
    return db_drone

@router.get("/", response_model=List[DroneRead])
def read_drones(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    # current_user: models.User = Depends(deps.get_current_active_operator_or_admin), # Protect
):
    """
    Retrieve a list of drones. (Admin/Operator)
    """
    statement = select(models.Drone).offset(skip).limit(limit)
    drones = session.exec(statement).all()
    return drones

@router.get("/{drone_id_str}", response_model=DroneRead)
def read_drone(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str,
    # current_user: models.User = Depends(deps.get_current_active_operator_or_admin), # Protect
):
    """
    Get drone by its public string ID. (Admin/Operator)
    """
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
    drone_in: DroneUpdate, # This now exists
    # current_user: models.User = Depends(deps.get_current_active_admin), # Protect
):
    """
    Update drone information. (Admin/Operator)
    """
    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    db_drone = session.exec(statement).first()
    if not db_drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")

    update_data = drone_in.model_dump(exclude_unset=True)
    db_drone.sqlmodel_update(update_data) # Use sqlmodel_update
    session.add(db_drone)
    session.commit()
    session.refresh(db_drone)
    return db_drone

# --- Endpoints for WebSocket Server Communication (Internal) ---

@router.post("/{drone_id_str}/telemetry", status_code=status.HTTP_201_CREATED)
def record_telemetry(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str, # Use the string ID from the path
    telemetry_in: DroneTelemetryCreate, # This now exists
    # request: Request # To check internal API token maybe?
    # internal_dep: bool = Depends(deps.verify_internal_request) # Add dependency for internal auth
):
    """
    Internal endpoint for the WebSocket server to persist telemetry data.
    """
    # Find the drone's internal DB ID using the string ID
    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = session.exec(statement).first()
    if not drone:
        # Log this error, as it indicates a mismatch between WS server and DB
        logging.error(f"Received telemetry for unknown drone ID string: {drone_id_str}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone with ID {drone_id_str} not found")

    # Create the telemetry record, linking it to the drone's internal ID
    # Ensure timestamp is handled correctly (e.g., parse from ISO string if needed)
    db_telemetry = models.DroneTelemetry(
        drone_id=drone.id,
        mission_id_str=telemetry_in.mission_id_str,
        timestamp=telemetry_in.timestamp, # Assuming schema handles conversion
        lat=telemetry_in.lat,
        lon=telemetry_in.lon,
        alt_m=telemetry_in.alt_m,
        speed_m_s=telemetry_in.speed_m_s,
        battery_pct=telemetry_in.battery_pct,
        flight_mode=telemetry_in.flight_mode,
        # Handle if payload is dict or string
        raw_payload_json=telemetry_in.raw_payload_json if isinstance(telemetry_in.raw_payload_json, str) else str(telemetry_in.raw_payload_json)
    )
    session.add(db_telemetry)

    # --- Update Drone's own status based on telemetry ---
    # This logic might be better placed in a dedicated service/task
    drone.current_lat = telemetry_in.lat
    drone.current_lon = telemetry_in.lon
    drone.current_battery_pct = telemetry_in.battery_pct
    drone.last_seen = telemetry_in.timestamp # Update last seen time

    # Map flight mode to DroneStatus (example, needs refinement)
    if telemetry_in.flight_mode in ["AUTO", "MISSION", "OFFBOARD"] and drone.status != models.DroneStatus.IN_MISSION:
         drone.status = models.DroneStatus.IN_MISSION
    elif telemetry_in.flight_mode == "RTL" and drone.status != models.DroneStatus.RETURNING:
         drone.status = models.DroneStatus.RETURNING
    elif telemetry_in.flight_mode == "LAND" and drone.status != models.DroneStatus.LANDING:
         drone.status = models.DroneStatus.LANDING
    # Add more logic based on flight_mode and potentially landed_state if sent
    session.add(drone)
    # --- End Drone Status Update ---

    session.commit()
    # No need to return anything complex, status 201 is enough
    return {"status": "Telemetry recorded"}


@router.post("/{drone_id_str}/events", status_code=status.HTTP_201_CREATED)
def record_event(
    *,
    session: Session = Depends(get_session),
    drone_id_str: str,
    event_in: DroneEventCreate, # This now exists
    # internal_dep: bool = Depends(deps.verify_internal_request) # Add dependency for internal auth
):
    """
    Internal endpoint for the WebSocket server to persist drone events.
    """
    statement = select(models.Drone).where(models.Drone.drone_id_str == drone_id_str)
    drone = session.exec(statement).first()
    if not drone:
        logging.error(f"Received event for unknown drone ID string: {drone_id_str}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone with ID {drone_id_str} not found")

    # --- Update Drone/Mission status based on specific events ---
    # This logic could also be in a separate service listening to events
    if event_in.event_type == models.EventType.LANDED:
         drone.status = models.DroneStatus.IDLE # Assume landed at base if type is LANDED
         session.add(drone)
         # If mission was active, mark mission completed/failed based on event details
         if event_in.mission_id_str:
             mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
             mission = session.exec(mission_statement).first()
             if mission and mission.status not in [models.MissionStatus.COMPLETED, models.MissionStatus.FAILED_EMERGENCY_LANDING]: # Avoid overwriting final state
                  # Determine final status based on event details (e.g., reason=RTL -> FAILED?)
                  final_status = models.MissionStatus.COMPLETED # Default
                  if event_in.details and "reason" in event_in.details:
                      if event_in.details["reason"] == "RTL": final_status = models.MissionStatus.FAILED_LOW_BATTERY # Example
                      # Add more failure mappings
                  mission.status = final_status
                  mission.updated_at = event_in.timestamp
                  session.add(mission)

    elif event_in.event_type == models.EventType.EMERGENCY_LANDING:
         drone.status = models.DroneStatus.MAINTENANCE # Requires check after emergency
         session.add(drone)
         if event_in.mission_id_str:
              mission_statement = select(models.Mission).where(models.Mission.mission_id_str == event_in.mission_id_str)
              mission = session.exec(mission_statement).first()
              if mission:
                  mission.status = models.MissionStatus.FAILED_EMERGENCY_LANDING
                  mission.failure_reason = event_in.details.get("reason", "Emergency Landing Triggered") if event_in.details else "Emergency Landing Triggered"
                  mission.updated_at = event_in.timestamp
                  session.add(mission)
    # Add more event-driven status updates here
    # --- End Status Update Logic ---

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
