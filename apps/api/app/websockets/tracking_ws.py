# apps/api/app/websockets/tracking_ws.py

import asyncio
import json
import logging
import uuid
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List
from enum import Enum
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, BackgroundTasks, Query, Request
from starlette.websockets import WebSocketState
from starlette.responses import JSONResponse
import jose.jwt as jwt
from jose.exceptions import JWTError
from pydantic import BaseModel, ValidationError, Field, field_validator, model_validator
from app.core.config import settings
from app.services.cache_service import IAsyncCacheClient, get_cache_client, RedisCacheClient

try:
    import structlog
    log = structlog.get_logger(__name__)
except ImportError:
    log = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

WEBSOCKET_TIMEOUT_SECONDS = 60 * 5
ACK_TIMEOUT_SECONDS = 10
ACK_RETRIES = 3
DRONE_SESSION_PREFIX = "drone_session:"
PENDING_ACK_PREFIX = "pending_ack:"
COMMAND_STATUS_PREFIX = "command_status:"
REDIS_ACK_TIMEOUT = ACK_TIMEOUT_SECONDS * (2**(ACK_RETRIES - 1)) + 5
TELEMETRY_INTERVAL_S = 10

connected_drones: Dict[str, Dict[str, Any]] = {}
connected_ui_clients: Set[WebSocket] = set()

async def broadcast_to_ui(message: dict):
    disconnected_clients: Set[WebSocket] = set()
    message_json = json.dumps(message, default=str)

    for client in list(connected_ui_clients):
        if client.client_state == WebSocketState.CONNECTED:
            try:
                await client.send_text(message_json)
            except Exception as e:
                log.warning(f"Failed to broadcast to UI client {client.client}: {e}. Marking for removal.")
                disconnected_clients.add(client)
        else:
            disconnected_clients.add(client)

    for client in disconnected_clients:
        connected_ui_clients.discard(client)

class EventType(str, Enum):
    TAKEOFF = "takeoff"
    LANDED = "landed"
    PAYLOAD_DROPPED = "payload_dropped"
    EMERGENCY_LANDING = "emergency_landing"
    GENERIC = "generic_event"

class NotificationType(str, Enum):
    DRONE_STATUS = "drone_status"
    ORDER_UPDATE = "order_update"
    SYSTEM_ALERT = "system_alert"
    SECURITY = "security"

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
    event_type: str
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
    status: str

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

class CommandGotoPayload(BaseModel):
    lat: float
    lon: float
    alt_m: float

class CommandPayload(BaseModel):
    action: str
    mission: Optional[CommandMissionPayload] = None
    goto: Optional[CommandGotoPayload] = None
    requires_ack: bool = True

    @model_validator(mode='after')
    def check_payload_matches_action(self, data: Any) -> Any:
        if isinstance(data, BaseModel):
             action = data.action
             mission = data.mission
             goto_payload = data.goto

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

async def register_drone(drone_id: str, websocket: WebSocket, cache: IAsyncCacheClient, meta: Optional[HandshakeMeta] = None):
    session_data = {
        "websocket": websocket,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "meta": meta.model_dump() if meta else {}
    }
    connected_drones[drone_id] = session_data

    redis_data = {
        "last_seen": session_data["last_seen"],
        "meta": session_data["meta"],
        "server_node_id": os.getenv("HOSTNAME", "node1"),
        "status": "connected"
    }
    await cache.set_json(f"{DRONE_SESSION_PREFIX}{drone_id}", redis_data)

    if isinstance(cache, RedisCacheClient):
        try:
            await cache._redis.publish("drone_connections", json.dumps({"drone_id": drone_id, "status": "connected"}))
        except Exception as e:
            log.error(f"Failed to publish drone connection event: {e}")

    log.info("Drone registered", drone_id=drone_id, meta=session_data["meta"])

async def unregister_drone(drone_id: str, cache: IAsyncCacheClient):
    session_info = connected_drones.pop(drone_id, None)
    if session_info:
        log.info("Drone unregistered", drone_id=drone_id)

        await cache.delete(f"{DRONE_SESSION_PREFIX}{drone_id}")

        if isinstance(cache, RedisCacheClient):
            try:
                await cache._redis.publish("drone_connections", json.dumps({"drone_id": drone_id, "status": "disconnected"}))
            except Exception as e:
                log.error(f"Failed to publish drone disconnection event: {e}")

        async def notify_disconnect():
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    headers = {"Authorization": f"Bearer {settings.INTERNAL_API_TOKEN}"} if settings.INTERNAL_API_TOKEN else {}
                    url = f"{settings.API_BASE_URL.rstrip('/')}/internal/drone_disconnected"
                    await client.post(url, json={"drone_id": drone_id}, headers=headers)
                    log.info("Notified main API about drone disconnect", drone_id=drone_id)
                except httpx.RequestError as e:
                    log.error(f"Failed to notify main API about drone disconnect", drone_id=drone_id, error=str(e))
                except Exception as e:
                     log.error(f"Unexpected error notifying disconnect", drone_id=drone_id, error=str(e))

        asyncio.create_task(notify_disconnect())

async def get_websocket(drone_id: str, cache: IAsyncCacheClient) -> Optional[WebSocket]:
    drone_info = connected_drones.get(drone_id)
    if drone_info:
        ws = drone_info["websocket"]
        if ws.client_state == WebSocketState.CONNECTED:
            try:
                await asyncio.wait_for(ws.send_json({"type": "ping"}), timeout=1.0)
                return ws
            except (asyncio.TimeoutError, Exception) as e:
                 log.warning("Ping failed, assuming stale connection", drone_id=drone_id, error=str(e))
                 await unregister_drone(drone_id, cache)
                 return None
        else:
            log.warning("Found disconnected websocket object in registry", drone_id=drone_id)
            await unregister_drone(drone_id, cache)
            return None
    return None

async def update_last_seen(drone_id: str, cache: IAsyncCacheClient):
    now_iso = datetime.now(timezone.utc).isoformat()
    if drone_id in connected_drones:
        connected_drones[drone_id]["last_seen"] = now_iso

    current_data = await cache.get_json(f"{DRONE_SESSION_PREFIX}{drone_id}")
    if current_data:
        current_data["last_seen"] = now_iso
        await cache.set_json(f"{DRONE_SESSION_PREFIX}{drone_id}", current_data)

async def verify_token(token: str, drone_id: str) -> bool:
    try:
        payload = jwt.decode(token, settings.DRONE_JWT_SECRET, algorithms=[settings.ALGORITHM])
        token_drone_id = payload.get("sub")
        if token_drone_id != drone_id:
             log.warning("Token drone_id mismatch", token_id=token_drone_id, path_id=drone_id)
             return False

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

async def persist_data(endpoint_path: str, data: dict):
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

async def handle_telemetry(websocket: WebSocket, data: dict, background_tasks: BackgroundTasks, cache: IAsyncCacheClient):
    try:
        telemetry = TelemetryMessage.model_validate(data)
        drone_id = telemetry.drone_id
        await update_last_seen(drone_id, cache)

        payload_to_persist = {
            "drone_id": drone_id,
            "mission_id_str": telemetry.payload.mission_id,
            "timestamp": telemetry.timestamp.isoformat(),
            "lat": telemetry.payload.lat, "lon": telemetry.payload.lon, "alt_m": telemetry.payload.alt_m,
            "speed_m_s": telemetry.payload.ground_speed_m_s, "battery_pct": telemetry.payload.battery_pct,
            "flight_mode": telemetry.payload.flight_mode,
            "raw_payload_json": telemetry.model_dump(mode='json')
        }

        background_tasks.add_task(persist_data, f"/drones/{drone_id}/telemetry", payload_to_persist)

    except ValidationError as e:
        log.warning("Invalid telemetry format", errors=e.errors(), data=data)
    except Exception as e:
        log.error("Error handling telemetry", error=str(e), exc_info=True)

def create_notification_from_event(event: EventMessage) -> Optional[Dict]:
    payload = event.payload
    title = f"Drone {event.drone_id} Update"
    body = f"Event: {payload.event_type}"
    notif_type = NotificationType.DRONE_STATUS

    if payload.event_type == EventType.TAKEOFF:
        title = "Drone Airborne"
        body = f"Drone {event.drone_id} has taken off for mission {payload.mission_id or 'N/A'}."
        notif_type = NotificationType.ORDER_UPDATE
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

    if title and body:
        return {
            "id": None,
            "type": notif_type.value,
            "title": title,
            "body": body,
            "created_at": event.timestamp.isoformat(),
        }
    return None

async def handle_event(websocket: WebSocket, data: dict, background_tasks: BackgroundTasks, cache: IAsyncCacheClient):
    try:
        event = EventMessage.model_validate(data)
        drone_id = event.drone_id
        await update_last_seen(drone_id, cache)

        payload_to_persist = {
            "drone_id": drone_id,
            "mission_id_str": event.payload.mission_id,
            "event_type": event.payload.event_type,
            "details": event.payload.details,
            "timestamp": event.timestamp.isoformat()
        }

        background_tasks.add_task(persist_data, f"/drones/{drone_id}/events", payload_to_persist)

        notification_payload = create_notification_from_event(event)
        if notification_payload:
            background_tasks.add_task(broadcast_to_ui, {
                "type": "notification",
                "payload": notification_payload
            })

        log.info("Event received", drone_id=drone_id, event_type=event.payload.event_type)

    except ValidationError as e:
        log.warning("Invalid event format", errors=e.errors(), data=data)
    except Exception as e:
        log.error("Error handling event", error=str(e), exc_info=True)

pending_ack_events: Dict[str, asyncio.Event] = {}

async def update_command_status(command_id: str, status: str, cache: IAsyncCacheClient):
    try:
        await cache.set(f"{COMMAND_STATUS_PREFIX}{command_id}", status, ttl=REDIS_ACK_TIMEOUT)
        log.debug("Command status updated in Redis", command_id=command_id, status=status)
    except Exception as e:
        log.error("Failed to update command status in Redis", command_id=command_id, error=str(e))

async def handle_ack(websocket: WebSocket, data: dict, background_tasks: BackgroundTasks, cache: IAsyncCacheClient):
    try:
        ack = AckMessage.model_validate(data)
        drone_id = ack.drone_id
        command_id = ack.command_id
        status = ack.status
        await update_last_seen(drone_id, cache)
        log.info("ACK received", drone_id=drone_id, command_id=command_id, status=status)

        if command_id in pending_ack_events:
            pending_ack_events[command_id].set()

        background_tasks.add_task(update_command_status, command_id, status, cache)

    except ValidationError as e:
        log.warning("Invalid ACK format", errors=e.errors(), data=data)
    except Exception as e:
        log.error("Error handling ACK", error=str(e), exc_info=True)

router = APIRouter()

@router.websocket("/drones/{drone_id}")
async def websocket_endpoint(websocket: WebSocket, drone_id: str, background_tasks: BackgroundTasks):
    await websocket.accept()

    cache: IAsyncCacheClient = getattr(websocket.app.state, "cache", None)
    if not cache:
        log.error("Cache client not initialized in app state.")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    authenticated = False
    log.info("Drone connection attempt", drone_id=drone_id, client=websocket.client)

    try:
        try:
            raw_handshake = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            handshake_data = json.loads(raw_handshake)
            handshake = HandshakeMessage.model_validate(handshake_data)

            if handshake.drone_id != drone_id:
                raise ValueError("Drone ID mismatch")

            if await verify_token(handshake.token, drone_id):
                authenticated = True
                await register_drone(drone_id, websocket, cache, handshake.meta)
                await websocket.send_json({"status": "connected", "drone_id": drone_id})
                log.info("Drone authenticated", drone_id=drone_id)
            else:
                raise ValueError("Invalid token")

        except (asyncio.TimeoutError, json.JSONDecodeError, ValidationError, ValueError) as e:
            reason = f"Authentication Failed: {e}"
            log.warning(f"{reason} (drone_id: {drone_id})")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=reason)
            return

        last_comm_time = datetime.now(timezone.utc)
        while authenticated and websocket.client_state == WebSocketState.CONNECTED:
            try:
                receive_timeout = TELEMETRY_INTERVAL_S * 2 + 5
                raw_message = await asyncio.wait_for(websocket.receive_text(), timeout=receive_timeout)
                last_comm_time = datetime.now(timezone.utc)
                message_data = json.loads(raw_message)
                message_type = message_data.get("type")

                if message_type == "telemetry":
                    await handle_telemetry(websocket, message_data, background_tasks, cache)
                elif message_type == "event":
                    await handle_event(websocket, message_data, background_tasks, cache)
                elif message_type == "ack":
                    await handle_ack(websocket, message_data, background_tasks, cache)
                elif message_type == "ping":
                    await update_last_seen(drone_id, cache)
                    await websocket.send_json({"type": "pong"})
                else:
                    log.warning("Unknown message type", drone_id=drone_id, type=message_type)

            except asyncio.TimeoutError:
                if datetime.now(timezone.utc) - last_comm_time > timedelta(seconds=WEBSOCKET_TIMEOUT_SECONDS):
                    log.warning(f"WebSocket inactivity timeout", drone_id=drone_id)
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Inactivity Timeout")
                    break
                else:
                    log.debug("Receive timeout, sending ping", drone_id=drone_id)
                    try:
                         await websocket.send_json({"type": "ping"})
                    except Exception:
                         log.warning("Ping failed after receive timeout, closing.", drone_id=drone_id)
                         break
            except json.JSONDecodeError:
                log.warning("Invalid JSON received", drone_id=drone_id)
            except Exception as e:
                log.error(f"WebSocket communication error (drone_id: {drone_id}): {e}", exc_info=True)
                break

    except WebSocketDisconnect as e:
        log.info(f"Drone disconnected", drone_id=drone_id, code=e.code, reason=e.reason)
    except Exception as e:
        log.error(f"Unexpected WebSocket error (drone_id: {drone_id}): {e}", exc_info=True)
        if websocket.client_state == WebSocketState.CONNECTED:
             await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        if authenticated and drone_id in connected_drones:
            await unregister_drone(drone_id, cache)

@router.websocket("/ui")
async def websocket_ui_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    await websocket.accept()
    connected_ui_clients.add(websocket)
    log.info(f"UI client connected: {websocket.client}")
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        log.info(f"UI client disconnected: {websocket.client}")
    except Exception as e:
         log.warning(f"Error with UI client {websocket.client}: {e}")
    finally:
        connected_ui_clients.discard(websocket)

async def wait_for_ack(command_id: str, timeout: float):
    ack_event = asyncio.Event()
    pending_ack_events[command_id] = ack_event
    try:
        await asyncio.wait_for(ack_event.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False
    finally:
        pending_ack_events.pop(command_id, None)

@router.post("/internal/send_command/{drone_id}", status_code=status.HTTP_202_ACCEPTED)
async def send_command_to_drone(
    drone_id: str,
    command_req: CommandMessage,
    background_tasks: BackgroundTasks,
    cache: IAsyncCacheClient = Depends(get_cache_client)
):
    websocket = await get_websocket(drone_id, cache)
    if not websocket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drone {drone_id} not connected or connection stale.")

    command = command_req.model_copy(update={"command_id": command_req.command_id or f"cmd-{uuid.uuid4().hex[:8]}"})
    command_id = command.command_id
    requires_ack = command.payload.requires_ack
    action = command.payload.action

    log.info("Sending command", drone_id=drone_id, action=action, command_id=command_id, requires_ack=requires_ack)

    async def _send_and_handle_ack_in_background():
        is_sent = False
        for attempt in range(ACK_RETRIES if requires_ack else 1):
            try:
                current_websocket = await get_websocket(drone_id, cache)
                if not current_websocket:
                    log.error("Drone disconnected before command could be sent/resent", drone_id=drone_id, command_id=command_id)
                    await update_command_status(command_id, "failed:disconnected", cache)
                    return

                await current_websocket.send_text(command.model_dump_json(exclude_none=True))
                is_sent = True
                log.debug(f"Command sent (Attempt {attempt + 1})", drone_id=drone_id, command_id=command_id)

                if not requires_ack:
                    await update_command_status(command_id, "sent_no_ack", cache)
                    return

                ack_timeout = ACK_TIMEOUT_SECONDS * (2**attempt)
                ack_received = await wait_for_ack(command_id, ack_timeout)

                if ack_received:
                    log.info("ACK received in time", drone_id=drone_id, command_id=command_id)
                    return
                else:
                    log.warning(f"ACK timeout (Attempt {attempt + 1}/{ACK_RETRIES})", drone_id=drone_id, command_id=command_id, timeout=ack_timeout)
                    if attempt == ACK_RETRIES - 1:
                        log.error(f"Command failed after {ACK_RETRIES} attempts (ACK timeout)", drone_id=drone_id, command_id=command_id)
                        await update_command_status(command_id, "failed:comms_timeout", cache)

                        async with httpx.AsyncClient(timeout=5.0) as client:
                             try:
                                headers = {"Authorization": f"Bearer {settings.INTERNAL_API_TOKEN}"} if settings.INTERNAL_API_TOKEN else {}
                                url = f"{settings.API_BASE_URL.rstrip('/')}/internal/command_timeout"
                                await client.post(url, json={"drone_id": drone_id, "command_id": command_id}, headers=headers)
                             except Exception as notify_err:
                                 log.error("Failed to notify API about command timeout", command_id=command_id, error=str(notify_err))
                        return

            except WebSocketDisconnect:
                log.error("Drone disconnected during send/wait", drone_id=drone_id, command_id=command_id)
                if is_sent:
                    await update_command_status(command_id, "failed:disconnected_after_send", cache)
                else:
                     await update_command_status(command_id, "failed:disconnected_before_send", cache)
                return
            except Exception as e:
                log.error(f"Error sending/waiting for command (Attempt {attempt + 1})", drone_id=drone_id, command_id=command_id, error=str(e), exc_info=True)
                if attempt == ACK_RETRIES - 1:
                    await update_command_status(command_id, f"failed:send_error - {e}", cache)
                await asyncio.sleep(1 * (2**attempt))

    background_tasks.add_task(_send_and_handle_ack_in_background)
    await update_command_status(command_id, "pending_send", cache)

    return {"status": "command_accepted", "command_id": command_id}

@router.get("/health")
async def health_check(cache: IAsyncCacheClient = Depends(get_cache_client)):
    status_data = {"status": "ok", "redis": "disabled"}
    if settings.USE_REDIS:
        try:
            if await cache.ping():
                status_data["redis"] = "connected"
            else:
                status_data["redis"] = "disconnected"
                status_data["status"] = "error"
        except Exception:
             status_data["redis"] = "error"
             status_data["status"] = "error"

    status_code = status.HTTP_200_OK if status_data["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=status_data, status_code=status_code)
