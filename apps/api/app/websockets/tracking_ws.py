# file: apps/api/app/websockets/tracking_ws.py (Add Broadcasting)
# --- Full Implementation ---

import asyncio
import json
import logging
import uuid
import os # Added missing import
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List # Added List
from enum import Enum # Added Enum

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, BackgroundTasks, Query # Added Query
from starlette.websockets import WebSocketState
from starlette.responses import JSONResponse # Added missing import
import jose.jwt as jwt
from jose.exceptions import JWTError
from pydantic import BaseModel, ValidationError, Field, field_validator, model_validator

from app.core.config import settings
# Assuming settings now include:
# REDIS_HOST, REDIS_PORT, USE_REDIS (bool)
# DRONE_JWT_SECRET, ALGORITHM (e.g., "HS256")
# API_BASE_URL (e.g., "http://api:8000/api/v1" or "http://localhost:8000/api/v1")
# INTERNAL_API_TOKEN (optional, for securing internal calls)

# --- Constants ---
WEBSOCKET_TIMEOUT_SECONDS = 60 * 5 # Timeout for inactive connections (if no ping/telemetry)
ACK_TIMEOUT_SECONDS = 10
ACK_RETRIES = 3
REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}" if settings.USE_REDIS else None
DRONE_SESSION_PREFIX = "drone_session:"
PENDING_ACK_PREFIX = "pending_ack:"
COMMAND_STATUS_PREFIX = "command_status:"
REDIS_ACK_TIMEOUT = ACK_TIMEOUT_SECONDS * (2**(ACK_RETRIES - 1)) + 5 # Slightly longer than max backoff
TELEMETRY_INTERVAL_S = 10 # Assuming a 10s interval for timeout calculation

# --- Logging ---
# Use structlog if available in the project, otherwise standard logging
try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Connection Management (Add UI Clients) ---
redis_client: Optional[redis.Redis] = None
# In-memory fallback / primary storage for websocket objects
connected_drones: Dict[str, Dict[str, Any]] = {}
connected_ui_clients: Set[WebSocket] = set() # Store active UI WebSockets

# --- Broadcasting Function ---
async def broadcast_to_ui(message: dict):
    """Sends a JSON message to all connected UI clients."""
    disconnected_clients: Set[WebSocket] = set()
    message_json = json.dumps(message, default=str) # Prepare JSON once

    # Iterate over a copy in case the set changes during iteration
    for client in list(connected_ui_clients):
        if client.client_state == WebSocketState.CONNECTED:
            try:
                await client.send_text(message_json)
            except Exception as e:
                log.warning(f"Failed to broadcast to UI client {client.client}: {e}. Marking for removal.")
                disconnected_clients.add(client)
        else:
            disconnected_clients.add(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        connected_ui_clients.discard(client)
        log.info(f"Removed disconnected UI client: {client.client}")

# --- Enums (Based on new helper function) ---
class EventType(str, Enum):
    TAKEOFF = "takeoff"
    LANDED = "landed"
    PAYLOAD_DROPPED = "payload_dropped"
    EMERGENCY_LANDING = "emergency_landing"
    # Add other potential events if needed
    GENERIC = "generic_event"

class NotificationType(str, Enum):
    DRONE_STATUS = "drone_status"
    ORDER_UPDATE = "order_update"
    SYSTEM_ALERT = "system_alert"
    SECURITY = "security"

# --- Pydantic Models for Message Schemas (Strict Validation) ---
class HandshakeMeta(BaseModel):
    firmware: Optional[str] = None
    companion: Optional[str] = None

class HandshakeMessage(BaseModel):
    type: str
    drone_id: str
    token: str
    meta: Optional[HandshakeMeta] = None

    @field_validator('type')
    @classmethod
    def check_type(cls, v: str):
        if v != "connect":
            raise ValueError('Type must be "connect"')
        return v

class TelemetryPayload(BaseModel):
    lat: float
    lon: float
    alt_m: float
    ground_speed_m_s: float
    battery_pct: int = Field(ge=0, le=100)
    mission_id: Optional[str] = None
    flight_mode: Optional[str] = None
    flags: Optional[List[str]] = None

class TelemetryMessage(BaseModel):
    type: str
    drone_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: TelemetryPayload

    @field_validator('type')
    @classmethod
    def check_type(cls, v: str):
        if v != "telemetry":
            raise ValueError('Type must be "telemetry"')
        return v

class EventPayload(BaseModel):
    event_type: str # Should ideally match EventType enum
    mission_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class EventMessage(BaseModel):
    type: str
    drone_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: EventPayload

    @field_validator('type')
    @classmethod
    def check_type(cls, v: str):
        if v != "event":
            raise ValueError('Type must be "event"')
        return v

class AckMessage(BaseModel):
    type: str
    command_id: str
    drone_id: str
    status: str # accepted | rejected | processing | completed | failed[:reason]

    @field_validator('type')
    @classmethod
    def check_type(cls, v: str):
        if v != "ack":
            raise ValueError('Type must be "ack"')
        return v

class CommandMissionWaypoint(BaseModel):
    lat: float
    lon: float
    alt_m: float

class CommandMissionPayload(BaseModel):
    mission_id: str
    waypoints: List[CommandMissionWaypoint]
    loiter_time_s: Optional[int] = None
    # Add other mission params if needed

class CommandGotoPayload(BaseModel):
    lat: float
    lon: float
    alt_m: float
    # Add speed, yaw if needed

class CommandPayload(BaseModel):
    action: str # start_mission|pause|resume|return_to_home|abort|goto|release_payload
    mission: Optional[CommandMissionPayload] = None
    goto: Optional[CommandGotoPayload] = None
    # Add other action payloads if needed (e.g., payload_options for release_payload)
    requires_ack: bool = True

    @model_validator(mode='after') # Use model_validator for Pydantic v2
    def check_payload_matches_action(cls, data: Any) -> Any:
        # Ensure correct payload is present for actions that require it
        if isinstance(data, BaseModel): # Check if it's a model instance
             action = data.action
             mission = data.mission
             goto_payload = data.goto # Renamed variable

             if action == "start_mission" and not mission:
                 raise ValueError("Missing 'mission' payload for 'start_mission' action")
             if action == "goto" and not goto_payload:
                 raise ValueError("Missing 'goto' payload for 'goto' action")
        return data


class CommandMessage(BaseModel):
    type: str
    command_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: CommandPayload

    @field_validator('type')
    @classmethod
    def check_type(cls, v: str):
        if v != "command":
            raise ValueError('Type must be "command"')
        return v

# --- Helper Functions ---
async def initialize_redis():
    global redis_client
    if settings.USE_REDIS and REDIS_URL and redis_client is None:
        try:
            redis_client = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
            await redis_client.ping()
            log.info("Connected to Redis for session management.")
        except Exception as e:
            log.error(f"Failed to connect to Redis: {e}. Falling back to in-memory session management.")
            redis_client = None

async def register_drone(drone_id: str, websocket: WebSocket, meta: Optional[HandshakeMeta] = None):
    session_data = {
        "websocket": websocket, # Store the actual object in memory
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "meta": meta.model_dump() if meta else {}
    }
    connected_drones[drone_id] = session_data

    if redis_client:
        # Store serializable data in Redis Hash
        redis_data = {
            "last_seen": session_data["last_seen"],
            "meta": json.dumps(session_data["meta"]),
            "server_node_id": os.getenv("HOSTNAME", "node1") # Identify which server holds the connection
        }
        await redis_client.hset(f"{DRONE_SESSION_PREFIX}{drone_id}", mapping=redis_data)
        await redis_client.publish("drone_connections", json.dumps({"drone_id": drone_id, "status": "connected"}))
    log.info("Drone registered", drone_id=drone_id, meta=session_data["meta"])

async def unregister_drone(drone_id: str):
    session_info = connected_drones.pop(drone_id, None) # Remove from memory
    if session_info:
        log.info("Drone unregistered", drone_id=drone_id)
        if redis_client:
            await redis_client.delete(f"{DRONE_SESSION_PREFIX}{drone_id}")
            await redis_client.publish("drone_connections", json.dumps({"drone_id": drone_id, "status": "disconnected"}))

        # Notify mission manager about unexpected disconnect via Background Task
        async def notify_disconnect():
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    headers = {"Authorization": f"Bearer {settings.INTERNAL_API_TOKEN}"} if settings.INTERNAL_API_TOKEN else {}
                    # Ensure API_BASE_URL is set correctly in settings
                    url = f"{settings.API_BASE_URL.rstrip('/')}/internal/drone_disconnected"
                    await client.post(url, json={"drone_id": drone_id}, headers=headers)
                    log.info("Notified main API about drone disconnect", drone_id=drone_id)
                except httpx.RequestError as e:
                    log.error(f"Failed to notify main API about drone disconnect", drone_id=drone_id, error=str(e))
                except Exception as e:
                     log.error(f"Unexpected error notifying disconnect", drone_id=drone_id, error=str(e))

        # Run notification in background
        asyncio.create_task(notify_disconnect())

async def get_websocket(drone_id: str) -> Optional[WebSocket]:
    drone_info = connected_drones.get(drone_id)
    if drone_info:
        ws = drone_info["websocket"]
        # Check if websocket is still active
        if ws.client_state == WebSocketState.CONNECTED:
            # Test connection with a ping (optional but recommended)
            try:
                await asyncio.wait_for(ws.send_json({"type": "ping"}), timeout=1.0)
                # Pong handling happens in the main loop
                return ws
            except (asyncio.TimeoutError, Exception) as e:
                 log.warning("Ping failed, assuming stale connection", drone_id=drone_id, error=str(e))
                 # Clean up stale connection proactively
                 await unregister_drone(drone_id)
                 return None
        else:
            # Websocket object exists but is disconnected, clean up
            log.warning("Found disconnected websocket object in registry", drone_id=drone_id)
            await unregister_drone(drone_id)
            return None
    return None # Not found in memory

async def update_last_seen(drone_id: str):
    now_iso = datetime.now(timezone.utc).isoformat()
    if drone_id in connected_drones:
        connected_drones[drone_id]["last_seen"] = now_iso
    if redis_client:
        await redis_client.hset(f"{DRONE_SESSION_PREFIX}{drone_id}", "last_seen", now_iso)

# --- Authentication ---
async def verify_token(token: str, drone_id: str) -> bool:
    try:
        payload = jwt.decode(token, settings.DRONE_JWT_SECRET, algorithms=[settings.ALGORITHM])
        # Add more checks: expiry, audience, issuer if needed
        token_drone_id = payload.get("sub") # Assuming 'sub' holds the drone_id
        if token_drone_id != drone_id:
             log.warning("Token drone_id mismatch", token_id=token_drone_id, path_id=drone_id)
             return False
        # Check expiry
        expiry = payload.get("exp")
        if expiry and datetime.now(timezone.utc) > datetime.fromtimestamp(expiry, timezone.utc):
            log.warning("Token expired", drone_id=drone_id)
            return False

        log.info("Token verified", drone_id=drone_id, payload=payload)
        return True
    except JWTError as e:
        log.warning(f"JWT verification failed", drone_id=drone_id, error=str(e))
        return False
    except Exception as e:
         log.error("Unexpected error during token verification", drone_id=drone_id, error=str(e))
         return False

# --- Persistence Task ---
async def persist_data(endpoint_path: str, data: dict):
    """Posts data to the main API asynchronously."""
    async with httpx.AsyncClient(base_url=settings.API_BASE_URL.rstrip('/'), timeout=10.0) as client:
        try:
            headers = {"Authorization": f"Bearer {settings.INTERNAL_API_TOKEN}"} if settings.INTERNAL_API_TOKEN else {}
            response = await client.post(endpoint_path, json=data, headers=headers)
            response.raise_for_status()
            log.debug(f"Data successfully persisted", endpoint=endpoint_path, status=response.status_code)
        except httpx.RequestError as e:
            log.error(f"Failed to persist data (Request Error)", endpoint=endpoint_path, error=str(e))
        except httpx.HTTPStatusError as e:
            log.error(f"Failed to persist data (HTTP Error)", endpoint=endpoint_path, status=e.response.status_code, response=e.response.text)
        except Exception as e:
             log.error("Unexpected error during persistence", endpoint=endpoint_path, error=str(e))

# --- Message Handlers ---
async def handle_telemetry(websocket: WebSocket, data: dict, background_tasks: BackgroundTasks):
    try:
        telemetry = TelemetryMessage.model_validate(data)
        drone_id = telemetry.drone_id
        await update_last_seen(drone_id)

        payload_to_persist = {
            "drone_id": drone_id, # Keep raw ID
            "mission_id_str": telemetry.payload.mission_id,
            "timestamp": telemetry.timestamp.isoformat(),
            "lat": telemetry.payload.lat, "lon": telemetry.payload.lon, "alt_m": telemetry.payload.alt_m,
            "speed_m_s": telemetry.payload.ground_speed_m_s, "battery_pct": telemetry.payload.battery_pct,
            "flight_mode": telemetry.payload.flight_mode,
            "raw_payload_json": telemetry.model_dump(mode='json') # Use Pydantic's JSON dump
        }
        # Assuming endpoint is /api/v1/drones/{drone_id_str}/telemetry
        background_tasks.add_task(persist_data, f"/drones/{drone_id}/telemetry", payload_to_persist)

    except ValidationError as e:
        log.warning("Invalid telemetry format", errors=e.errors(), data=data)
    except Exception as e:
        log.error("Error handling telemetry", error=str(e), exc_info=True)

# --- Helper to create notification content (Example) ---
def create_notification_from_event(event: EventMessage) -> Optional[Dict]:
    payload = event.payload
    title = f"Drone {event.drone_id} Update"
    body = f"Event: {payload.event_type}"
    notif_type = NotificationType.DRONE_STATUS # Default type

    if payload.event_type == EventType.TAKEOFF:
        title = "Drone Airborne"
        body = f"Drone {event.drone_id} has taken off for mission {payload.mission_id or 'N/A'}."
        notif_type = NotificationType.ORDER_UPDATE # Link to order
    elif payload.event_type == EventType.PAYLOAD_DROPPED:
        title = "Package Delivered (Estimated)"
        body = f"Drone {event.drone_id} reported payload dropped for mission {payload.mission_id or 'N/A'}."
        notif_type = NotificationType.ORDER_UPDATE
    elif payload.event_type == EventType.LANDED:
        title = "Drone Landed"
        body = f"Drone {event.drone_id} has landed. Reason: {payload.details.get('reason', 'Mission End') if payload.details else 'Mission End'}."
    elif payload.event_type == EventType.EMERGENCY_LANDING:
        title = f"⚠️ EMERGENCY: Drone {event.drone_id}"
        body = f"Emergency landing initiated. Reason: {payload.details.get('reason', 'Unknown') if payload.details else 'Unknown'}."
        notif_type = NotificationType.SYSTEM_ALERT
    # Add more mappings for other EventTypes

    # Only return if we have meaningful content
    if title and body:
        return {
            "id": None, # Let frontend handle display ID or fetch full notification later
            "type": notif_type.value,
            "title": title,
            "body": body,
            "created_at": event.timestamp.isoformat(),
        }
    return None

# --- Modify handle_event to broadcast ---
async def handle_event(websocket: WebSocket, data: dict, background_tasks: BackgroundTasks):
    try:
        event = EventMessage.model_validate(data)
        drone_id = event.drone_id
        await update_last_seen(drone_id)

        # Persist event
        payload_to_persist = {
            "drone_id": drone_id, # Keep raw ID
            "mission_id_str": event.payload.mission_id,
            "event_type": event.payload.event_type,
            "details": event.payload.details,
            "timestamp": event.timestamp.isoformat()
        }
        # Assuming endpoint is /api/v1/drones/{drone_id_str}/events
        background_tasks.add_task(persist_data, f"/drones/{drone_id}/events", payload_to_persist)

        # --- 💡 Broadcast event as a notification ---
        # Format a user-friendly notification based on the event
        notification_payload = create_notification_from_event(event)
        if notification_payload:
            background_tasks.add_task(broadcast_to_ui, {
                "type": "notification",
                "payload": notification_payload
            })
            # TODO: Also save this notification to the DB for the relevant user(s)?

        log.info("Event received", drone_id=drone_id, event_type=event.payload.event_type)

    except ValidationError as e:
        log.warning("Invalid event format", errors=e.errors(), data=data)
    except Exception as e:
        log.error("Error handling event", error=str(e), exc_info=True)


# Store events to signal when an ACK is received for a command_id
pending_ack_events: Dict[str, asyncio.Event] = {}

async def handle_ack(websocket: WebSocket, data: dict, background_tasks: BackgroundTasks):
    try:
        ack = AckMessage.model_validate(data)
        drone_id = ack.drone_id
        command_id = ack.command_id
        status = ack.status
        await update_last_seen(drone_id)
        log.info("ACK received", drone_id=drone_id, command_id=command_id, status=status)

        # Signal the waiting task, if any
        if command_id in pending_ack_events:
            pending_ack_events[command_id].set()
            # Remove immediately after signaling? Or keep for potential status update?
            # del pending_ack_events[command_id] # Let the sending task clean up

        # Update command status in Redis/DB via background task
        background_tasks.add_task(update_command_status, command_id, status)

    except ValidationError as e:
        log.warning("Invalid ACK format", errors=e.errors(), data=data)
    except Exception as e:
        log.error("Error handling ACK", error=str(e), exc_info=True)

async def update_command_status(command_id: str, status: str):
    """Updates the command status in Redis (or potentially DB)."""
    if redis_client:
        try:
            await redis_client.setex(f"{COMMAND_STATUS_PREFIX}{command_id}", REDIS_ACK_TIMEOUT, status)
            log.debug("Command status updated in Redis", command_id=command_id, status=status)
        except Exception as e:
            log.error("Failed to update command status in Redis", command_id=command_id, error=str(e))
    # Add DB update logic here if needed


# --- Router Definition ---
router = APIRouter()

@router.on_event("startup")
async def startup_event():
    await initialize_redis()
    log.info("WebSocket Router Started.")

@router.websocket("/drones/{drone_id}") # Removed /ws prefix as it's handled in main.py
async def websocket_endpoint(websocket: WebSocket, drone_id: str, background_tasks: BackgroundTasks):
    await websocket.accept()
    authenticated = False
    log.info("Drone connection attempt", drone_id=drone_id, client=websocket.client)

    try:
        # 1. Authentication Handshake
        try:
            raw_handshake = await asyncio.wait_for(websocket.receive_text(), timeout=15.0) # Increased timeout
            handshake_data = json.loads(raw_handshake)
            handshake = HandshakeMessage.model_validate(handshake_data)

            if handshake.drone_id != drone_id:
                raise ValueError("Drone ID mismatch")

            if await verify_token(handshake.token, drone_id): # Pass drone_id for verification
                authenticated = True
                await register_drone(drone_id, websocket, handshake.meta)
                await websocket.send_json({"status": "connected", "drone_id": drone_id})
                log.info("Drone authenticated", drone_id=drone_id)
            else:
                raise ValueError("Invalid token")

        except (asyncio.TimeoutError, json.JSONDecodeError, ValidationError, ValueError) as e:
            reason = f"Authentication Failed: {e}"
            log.warning(reason, drone_id=drone_id)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=reason)
            return

        # 2. Main Communication Loop
        last_comm_time = datetime.now(timezone.utc)
        while authenticated and websocket.client_state == WebSocketState.CONNECTED:
            try:
                # Use a slightly longer timeout than telemetry interval + buffer
                receive_timeout = TELEMETRY_INTERVAL_S * 2 + 5
                raw_message = await asyncio.wait_for(websocket.receive_text(), timeout=receive_timeout)
                last_comm_time = datetime.now(timezone.utc) # Reset timer on any message
                message_data = json.loads(raw_message)
                message_type = message_data.get("type")

                if message_type == "telemetry":
                    await handle_telemetry(websocket, message_data, background_tasks)
                elif message_type == "event":
                    await handle_event(websocket, message_data, background_tasks)
                elif message_type == "ack":
                    await handle_ack(websocket, message_data, background_tasks)
                elif message_type == "ping":
                    await update_last_seen(drone_id)
                    await websocket.send_json({"type": "pong"})
                else:
                    log.warning("Unknown message type", drone_id=drone_id, type=message_type)

            except asyncio.TimeoutError:
                # Check if timeout is expected (no messages for a while)
                if datetime.now(timezone.utc) - last_comm_time > timedelta(seconds=WEBSOCKET_TIMEOUT_SECONDS):
                    log.warning(f"WebSocket inactivity timeout", drone_id=drone_id)
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Inactivity Timeout")
                    break
                else:
                    # Timeout happened but within inactivity limit, likely just no message yet.
                    # Send a ping to check connection health.
                    log.debug("Receive timeout, sending ping", drone_id=drone_id)
                    try:
                         await websocket.send_json({"type": "ping"})
                    except Exception:
                         log.warning("Ping failed after receive timeout, closing.", drone_id=drone_id)
                         break # Break loop, finally block will handle unregister
            except json.JSONDecodeError:
                log.warning("Invalid JSON received", drone_id=drone_id)
            except Exception as e:
                log.error("WebSocket communication error", drone_id=drone_id, error=str(e), exc_info=True)
                break # Close connection on unexpected errors

    except WebSocketDisconnect as e:
        log.info(f"Drone disconnected", drone_id=drone_id, code=e.code, reason=e.reason)
    except Exception as e:
        log.error(f"Unexpected WebSocket error", drone_id=drone_id, error=str(e), exc_info=True)
        if websocket.client_state == WebSocketState.CONNECTED:
             await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        # Ensure unregistration happens regardless of how the loop/connection ends
        if authenticated and drone_id in connected_drones: # Check if it was ever registered
            await unregister_drone(drone_id)


# --- 💡 New WebSocket Endpoint for UI Clients ---
@router.websocket("/ui")
async def websocket_ui_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """Handles connections from UI clients for receiving broadcasts."""
    # Optional: Authenticate UI users based on token/session from query param or initial message
    user_id = None
    if token:
        # Placeholder: Validate user token (e.g., using deps.get_current_user logic adapted for WS)
        # try:
        #     # Use the main app's SECRET_KEY and ALGORITHM for user tokens
        #     payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        #     user_id = payload.get("sub") # Assuming 'sub' has user ID
        #     if not user_id: raise ValueError("Invalid token payload")
        # except Exception as e:
        #     await websocket.accept() # Accept then close immediately
        #     await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"Authentication failed: {e}")
        #     return
        pass # Allow unauthenticated for now for simplicity

    await websocket.accept()
    connected_ui_clients.add(websocket)
    log.info(f"UI client connected: {websocket.client}" + (f" (User: {user_id})" if user_id else ""))
    try:
        while True:
            # Keep connection open, handle pings or specific UI messages
            message = await websocket.receive_text()
            data = json.loads(message)
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            # Add other UI -> Server message handling if needed
    except WebSocketDisconnect:
        log.info(f"UI client disconnected: {websocket.client}")
    except Exception as e:
         log.warning(f"Error with UI client {websocket.client}: {e}")
    finally:
        connected_ui_clients.discard(websocket)


# --- Internal REST Endpoint for Sending Commands ---

# Helper to manage the ACK waiting tasks safely
async def wait_for_ack(command_id: str, timeout: float):
    ack_event = asyncio.Event()
    pending_ack_events[command_id] = ack_event
    try:
        await asyncio.wait_for(ack_event.wait(), timeout=timeout)
        return True # ACK received
    except asyncio.TimeoutError:
        return False # Timeout occurred
    finally:
        # Clean up the event reference regardless of outcome
        pending_ack_events.pop(command_id, None)

@router.post("/internal/send_command/{drone_id}", status_code=status.HTTP_202_ACCEPTED)
async def send_command_to_drone(drone_id: str, command_req: CommandMessage, background_tasks: BackgroundTasks):
    websocket = await get_websocket(drone_id)
    if not websocket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone {drone_id} not connected or connection stale.")

    # Assign a unique command ID if not provided (though client should provide)
    command = command_req.model_copy(update={"command_id": command_req.command_id or f"cmd-{uuid.uuid4().hex[:8]}"})
    command_id = command.command_id
    requires_ack = command.payload.requires_ack
    action = command.payload.action

    log.info("Sending command", drone_id=drone_id, action=action, command_id=command_id, requires_ack=requires_ack)

    async def _send_and_handle_ack_in_background():
        is_sent = False
        for attempt in range(ACK_RETRIES if requires_ack else 1):
            try:
                current_websocket = await get_websocket(drone_id) # Re-check connection
                if not current_websocket:
                    log.error("Drone disconnected before command could be sent/resent", drone_id=drone_id, command_id=command_id)
                    await update_command_status(command_id, "failed:disconnected")
                    return # Stop trying

                await current_websocket.send_text(command.model_dump_json(exclude_none=True))
                is_sent = True
                log.debug(f"Command sent (Attempt {attempt + 1})", drone_id=drone_id, command_id=command_id)

                if not requires_ack:
                    await update_command_status(command_id, "sent_no_ack")
                    return # Success for non-ACK commands

                # Wait for ACK with exponential backoff timeout
                ack_timeout = ACK_TIMEOUT_SECONDS * (2**attempt)
                ack_received = await wait_for_ack(command_id, ack_timeout)

                if ack_received:
                    log.info("ACK received in time", drone_id=drone_id, command_id=command_id)
                    # Status is updated by handle_ack, just exit
                    return
                else:
                    log.warning(f"ACK timeout (Attempt {attempt + 1}/{ACK_RETRIES})", drone_id=drone_id, command_id=command_id, timeout=ack_timeout)
                    if attempt == ACK_RETRIES - 1:
                        log.error(f"Command failed after {ACK_RETRIES} attempts (ACK timeout)", drone_id=drone_id, command_id=command_id)
                        await update_command_status(command_id, "failed:comms_timeout")
                        # TODO: Notify operators via API call or other mechanism
                        async with httpx.AsyncClient(timeout=5.0) as client:
                             try:
                                headers = {"Authorization": f"Bearer {settings.INTERNAL_API_TOKEN}"} if settings.INTERNAL_API_TOKEN else {}
                                url = f"{settings.API_BASE_URL.rstrip('/')}/internal/command_timeout"
                                await client.post(url, json={"drone_id": drone_id, "command_id": command_id}, headers=headers)
                             except Exception as notify_err:
                                 log.error("Failed to notify API about command timeout", command_id=command_id, error=str(notify_err))
                        return # Failed after retries

            except WebSocketDisconnect:
                log.error("Drone disconnected during send/wait", drone_id=drone_id, command_id=command_id)
                if is_sent: # If it was sent at least once before disconnect
                    await update_command_status(command_id, "failed:disconnected_after_send")
                else:
                     await update_command_status(command_id, "failed:disconnected_before_send")
                return # Stop trying
            except Exception as e:
                log.error(f"Error sending/waiting for command (Attempt {attempt + 1})", drone_id=drone_id, command_id=command_id, error=str(e), exc_info=True)
                if attempt == ACK_RETRIES - 1:
                    await update_command_status(command_id, f"failed:send_error - {e}")
                await asyncio.sleep(1 * (2**attempt)) # Wait before next retry

    # Add the task to background tasks for immediate 202 response
    background_tasks.add_task(_send_and_handle_ack_in_background)
    await update_command_status(command_id, "pending_send") # Initial status

    return {"status": "command_accepted", "command_id": command_id}


# --- Health & Metrics ---
@router.get("/health") # Changed from root to /health
async def health_check():
    response = {"status": "ok", "redis_connected": False}
    if redis_client:
        try:
            await redis_client.ping()
            response["redis_connected"] = True
        except Exception:
             response["status"] = "degraded" # Indicate partial failure
             log.warning("Health check: Redis ping failed.")
    elif settings.USE_REDIS:
         response["status"] = "degraded" # Configured to use Redis but not connected
         log.warning("Health check: Configured for Redis but not connected.")

    # Add DB check if crucial for WS server
    # try:
    #     async with async_session_maker() as session:
    #         await session.execute(select(1))
    # except Exception:
    #     response["status"] = "degraded"
    #     response["db_connected"] = False

    status_code = 200 if response["status"] == "ok" else 503
    return JSONResponse(content=response, status_code=status_code)
