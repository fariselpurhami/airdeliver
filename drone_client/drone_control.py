# drone_client/drone-control.py

import asyncio
import json
import logging
import os
import uuid
import time
import httpx
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Dict, Any, Optional, Tuple, List, Set 

import websockets
from mavsdk import System
from mavsdk.action import ActionError
from mavsdk.mission import MissionItem, MissionPlan, MissionError
from mavsdk.telemetry import LandedState, FlightMode, GpsInfo, Battery, Health, Position
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, Field

load_dotenv() 

DRONE_ID = os.getenv("DRONE_ID")
WEBSOCKET_URI_BASE = os.getenv("WEBSOCKET_URI")
MAVLINK_CONNECTION = os.getenv("MAVLINK_CONNECTION") 
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000/api/v1")

if not all([DRONE_ID, WEBSOCKET_URI_BASE, MAVLINK_CONNECTION, AUTH_TOKEN]):
    raise ValueError("One or more critical environment variables are not set.")

TELEMETRY_INTERVAL_S = 2.0
HEARTBEAT_TIMEOUT_S = 30.0 
RECONNECT_DELAY_S = 5.0

log = logging.getLogger("DroneCompanion")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not log.hasHandlers():
    log.addHandler(handler)

class DroneState(Enum):
    BOOTING = auto()
    DISCONNECTED_PIXHAWK = auto()
    CONNECTING_PIXHAWK = auto()
    GETTING_JWT = auto()
    DISCONNECTED_SERVER = auto()
    CONNECTING_SERVER = auto()
    IDLE = auto()
    PREFLIGHT_CHECKS = auto()
    ARMING = auto()
    TAKING_OFF = auto()
    IN_TRANSIT = auto()
    PAUSED = auto()
    RETURNING = auto()
    LANDING = auto()
    MISSION_COMPLETED = auto()
    MISSION_FAILED = auto()
    EMERGENCY_LANDING = auto()

class CommandMessage(BaseModel):
    command: str
    payload: Optional[Dict[str, Any]] = None

class DroneCompanion:
    def __init__(self, drone_id: str, ws_uri_base: str, mavlink_conn: str, api_token: str):
        self.drone_id = drone_id
        self.ws_uri_base = ws_uri_base.rstrip('/')
        self.mavlink_conn = mavlink_conn
        self.api_token = api_token
        self.jwt_token: Optional[str] = None
        self.jwt_expires: datetime = datetime.now(timezone.utc)

        self.mavsdk_drone = System()
        self.current_state = DroneState.BOOTING
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.command_queue = asyncio.Queue()
        self.active_mission_id: Optional[str] = None
        self.last_server_comm_time: Optional[datetime] = None
        self._tasks: Set[asyncio.Task] = set()
        self.http_client = httpx.AsyncClient(base_url=API_BASE_URL)

        log.info(f"[{self.drone_id}] Initializing Companion...")

    async def _start_task(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard) 
        return task

    async def _cancel_all_tasks(self):
        log.debug(f"[{self.drone_id}] Cancelling {len(self._tasks)} tasks...")
        for task in list(self._tasks): 
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        log.debug(f"[{self.drone_id}] All tasks cancelled.")

    async def _update_state(self, new_state: DroneState, reason: Optional[str] = None):
        if self.current_state != new_state:
            old_state = self.current_state.name
            self.current_state = new_state
            log.info(f"[{self.drone_id}] State Change: {old_state} -> {new_state.name}" + (f" (Reason: {reason})" if reason else ""))
            if self.websocket and self.websocket.open and new_state not in [DroneState.CONNECTING_SERVER, DroneState.GETTING_JWT]:
                 await self._send_event(f"state_{new_state.name.lower()}", details={"previous_state": old_state, "reason": reason})

    async def _get_jwt_token(self) -> bool:
        await self._update_state(DroneState.GETTING_JWT)
        log.info(f"[{self.drone_id}] Requesting JWT from API...")
        try:
            headers = {"Authorization": f"Bearer {self.api_token}"}
            response = await self.http_client.post(f"/auth/drone-token/{self.drone_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("access_token")
                self.jwt_expires = datetime.now(timezone.utc) + timedelta(minutes=data.get("expires_in_minutes", 55))
                log.info(f"[{self.drone_id}] JWT obtained, valid until {self.jwt_expires.isoformat()}.")
                await self._update_state(DroneState.DISCONNECTED_SERVER, "JWT Acquired")
                return True
            else:
                reason = f"Failed to get JWT: {response.status_code} - {response.text}"
                log.error(f"[{self.drone_id}] {reason}")
                await self._update_state(DroneState.GETTING_JWT, reason)
                return False
        except httpx.RequestError as e:
            reason = f"HTTP error getting JWT: {e}"
            log.error(f"[{self.drone_id}] {reason}")
            await self._update_state(DroneState.GETTING_JWT, reason)
            return False
        
    async def _check_jwt(self) -> bool:
        if not self.jwt_token or datetime.now(timezone.utc) > (self.jwt_expires - timedelta(minutes=5)):
            log.warning(f"[{self.drone_id}] JWT is missing or expiring. Refreshing...")
            return await self._get_jwt_token()
        return True

    async def _connect_to_pixhawk(self):
        await self._update_state(DroneState.CONNECTING_PIXHAWK)
        log.info(f"[{self.drone_id}] Connecting to Pixhawk: {self.mavlink_conn}")

        # Final Fix: Add a robust retry loop for connection resilience
        MAX_ATTEMPTS = 10
        for attempt in range(MAX_ATTEMPTS):
            try:
                await self.mavsdk_drone.connect(system_address=self.mavlink_conn)

                # Wait for system to confirm connection (up to 30s)
                await asyncio.wait_for(self._wait_for_pixhawk_connection(), timeout=30.0)

                log.info(f"[{self.drone_id}] Pixhawk connected! (Attempt {attempt + 1}/{MAX_ATTEMPTS})")
                await self._update_state(DroneState.GETTING_JWT)
                return True

            except asyncio.TimeoutError:
                log.warning(f"[{self.drone_id}] Attempt {attempt + 1}/{MAX_ATTEMPTS} timed out.")
                # We catch timeout here, but let the loop continue
            except Exception as e:
                # Catch hard connection errors (e.g., port not open, invalid address)
                log.warning(f"[{self.drone_id}] Connect attempt {attempt + 1} failed: {e}")
                # We sleep briefly between attempts to allow the port to open
            
            await asyncio.sleep(RECONNECT_DELAY_S)

        # If the loop finishes without success after all attempts
        log.error(f"[{self.drone_id}] Permanent connection failure after {MAX_ATTEMPTS} attempts.")
        await self._update_state(DroneState.DISCONNECTED_PIXHAWK, "Permanent Connect Failure")
        return False

    async def _wait_for_pixhawk_connection(self):
         async for state in self.mavsdk_drone.core.connection_state():
            if state.is_connected:
                return

    async def _connect_to_server(self):
        if not await self._check_jwt():
            return False
            
        await self._update_state(DroneState.CONNECTING_SERVER)
        ws_url_with_token = f"{self.ws_uri_base.rstrip('/')}/{self.jwt_token}"
        log.info(f"[{self.drone_id}] Connecting to WebSocket Server...")
        
        try:
            self.websocket = await websockets.connect(ws_url_with_token, ping_interval=20, ping_timeout=10)
            self.last_server_comm_time = datetime.now(timezone.utc)
            log.info(f"[{self.drone_id}] WebSocket Server connected.")
            await self._update_state(DroneState.IDLE)
            return True
        except websockets.exceptions.InvalidStatusCode as e:
            reason = f"WebSocket connection failed: {e.status_code}"
            log.error(f"[{self.drone_id}] {reason}")
            if e.status_code == 4001:
                log.error(f"[{self.drone_id}] Server rejected token. Forcing refresh.")
                self.jwt_token = None
            await self._update_state(DroneState.DISCONNECTED_SERVER, reason)
            return False
        except Exception as e:
            reason = f"WebSocket connection failed: {e}"
            log.error(f"[{self.drone_id}] {reason}")
            await self._update_state(DroneState.DISCONNECTED_SERVER, reason)
            return False

    async def _ensure_connection(self) -> bool:
        if not self.mavsdk_drone.core.is_connected():
            log.warning(f"[{self.drone_id}] Pixhawk disconnected.")
            await self._update_state(DroneState.DISCONNECTED_PIXHAWK, "Connection Lost")
            await self._cancel_all_tasks() 
            if self.websocket and self.websocket.open:
                await self.websocket.close() 
                self.websocket = None
            return False 

        if not self.websocket or not self.websocket.open:
            log.warning(f"[{self.drone_id}] WebSocket server disconnected.")
            await self._update_state(DroneState.DISCONNECTED_SERVER, "Connection Lost")
            await self._cancel_all_tasks() 
            return False 

        if self.last_server_comm_time and \
           (datetime.now(timezone.utc) - self.last_server_comm_time > timedelta(seconds=HEARTBEAT_TIMEOUT_S)):
            log.error(f"[{self.drone_id}] Server communication timeout ({HEARTBEAT_TIMEOUT_S}s).")
            await self.websocket.close()
            self.websocket = None
            await self._update_state(DroneState.DISCONNECTED_SERVER, "Communication Timeout")
            await self._cancel_all_tasks()
            return False

        return True 

    async def _send_json(self, message: dict):
         if self.websocket and self.websocket.open:
             try:
                 await self.websocket.send(json.dumps(message, default=str)) 
                 self.last_server_comm_time = datetime.now(timezone.utc) 
             except websockets.exceptions.ConnectionClosed:
                 await self._update_state(DroneState.DISCONNECTED_SERVER, "Send Failed")
             except Exception as e:
                  log.error(f"[{self.drone_id}] Error sending message: {e}")
         else:
             log.warning(f"[{self.drone_id}] Cannot send message, WebSocket not connected.")

    async def _send_event(self, event_type: str, details: Optional[Dict] = None):
        payload = {
            "event_type": models.EventType[event_type.upper()].value if hasattr(models.EventType, event_type.upper()) else event_type,
            "mission_id_str": self.active_mission_id,
            "drone_id": self.drone_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        }
        event_msg = {"type": "event", "payload": payload}
        await self._send_json(event_msg)
        log.info(f"[{self.drone_id}] Event Sent: {event_type}")

    async def _listen_for_server_commands(self):
        log.info(f"[{self.drone_id}] Starting Command Listener...")
        while self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING, DroneState.GETTING_JWT]:
            try:
                if not await self._ensure_connection(): break

                message_str = await asyncio.wait_for(self.websocket.recv(), timeout=HEARTBEAT_TIMEOUT_S)
                self.last_server_comm_time = datetime.now(timezone.utc) 
                
                await self.command_queue.put(message_str)

            except asyncio.TimeoutError:
                pass
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException) as e:
                log.warning(f"[{self.drone_id}] Command listener connection closed: {e}")
                await self._update_state(DroneState.DISCONNECTED_SERVER, "Listener Closed")
                break 
            except Exception as e:
                log.error(f"[{self.drone_id}] Error in command listener: {e}")
                await self._update_state(DroneState.DISCONNECTED_SERVER, f"Listener Error: {e}")
                break
        log.info(f"[{self.drone_id}] Command Listener stopped.")

    async def _send_telemetry_loop(self):
        log.info(f"[{self.drone_id}] Starting Telemetry Loop...")
        while self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING, DroneState.GETTING_JWT]:
            try:
                if not await self._ensure_connection(): break

                async_tasks = {
                    "position": asyncio.create_task(self.mavsdk_drone.telemetry.position().__aiter__().__anext__()),
                    "velocity": asyncio.create_task(self.mavsdk_drone.telemetry.velocity_ned().__aiter__().__anext__()),
                    "battery": asyncio.create_task(self.mavsdk_drone.telemetry.battery().__aiter__().__anext__()),
                    "flight_mode": asyncio.create_task(self.mavsdk_drone.telemetry.flight_mode().__aiter__().__anext__()),
                    "landed_state": asyncio.create_task(self.mavsdk_drone.telemetry.landed_state().__aiter__().__anext__()),
                }
                await asyncio.wait(async_tasks.values()) 
                
                pos: Optional[Position] = async_tasks["position"].result()
                vel = async_tasks["velocity"].result()
                bat: Optional[Battery] = async_tasks["battery"].result()
                fm: Optional[FlightMode] = async_tasks["flight_mode"].result()
                ls: Optional[LandedState] = async_tasks["landed_state"].result()

                if not all([pos, vel, bat, fm, ls]):
                     await asyncio.sleep(TELEMETRY_INTERVAL_S)
                     continue

                battery_pct = int(bat.remaining_percent * 100)
                
                if ls == LandedState.ON_GROUND and self.current_state in [DroneState.LANDING, DroneState.RETURNING, DroneState.EMERGENCY_LANDING]:
                     log.info(f"[{self.drone_id}] Detected landing completion.")
                     final_state = DroneState.IDLE
                     if self.active_mission_id:
                         final_state = DroneState.MISSION_COMPLETED if self.current_state != DroneState.EMERGENCY_LANDING else DroneState.MISSION_FAILED
                     await self._send_event("landed", details={"reason": self.current_state.name})
                     await self._update_state(final_state, "Landed")
                     self.active_mission_id = None 

                telemetry_payload = {
                    "drone_id": self.drone_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "mission_id_str": self.active_mission_id,
                    "lat": pos.latitude_deg, "lon": pos.longitude_deg, "alt_m": pos.relative_altitude_m,
                    "ground_speed_m_s": (vel.north_m_s**2 + vel.east_m_s**2)**0.5,
                    "battery_pct": battery_pct,
                    "flight_mode": fm.name,
                }
                telemetry_msg = { 
                    "type": "telemetry",
                    "payload": telemetry_payload
                }
                await self._send_json(telemetry_msg)

            except StopAsyncIteration:
                log.warning(f"[{self.drone_id}] Telemetry stream ended unexpectedly.")
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException):
                await self._update_state(DroneState.DISCONNECTED_SERVER, "Telemetry Send Failed")
                break 
            except Exception as e:
                log.error(f"[{self.drone_id}] Error in telemetry loop: {e}")
            finally:
                 if self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING, DroneState.GETTING_JWT]:
                     await asyncio.sleep(TELEMETRY_INTERVAL_S) 
                 else:
                      break 

        log.info(f"[{self.drone_id}] Telemetry Loop stopped.")

    async def _process_command_queue(self):
        log.info(f"[{self.drone_id}] Starting Command Processor...")
        while self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING, DroneState.GETTING_JWT]:
            message_str = await self.command_queue.get()
            try:
                command_msg = CommandMessage.model_validate_json(message_str)
                action = command_msg.command
                payload = command_msg.payload or {}
                
                log.info(f"Processing command: {action}")

                if action == "start_mission":
                    await self.execute_mission(payload.get("mission_id"), payload.get("waypoints"))
                elif action == "return_to_home":
                    await self.execute_return_to_home()
                else:
                    log.warning(f"Unknown or invalid action: {action}")

            except ValidationError as e:
                 log.warning(f"Invalid command format: {e.errors()} | Raw: {message_str}")
            except Exception as e:
                 log.error(f"Error processing command: {e}")
            finally:
                self.command_queue.task_done()
        log.info(f"[{self.drone_id}] Command Processor stopped.")

    async def execute_mission(self, mission_id: str, waypoints: List[Dict]):
        if self.current_state != DroneState.IDLE:
            return
        
        if not mission_id or not waypoints:
            log.error("Mission command missing mission_id or waypoints")
            return
            
        self.active_mission_id = mission_id
        log.info(f"[{self.drone_id}] Starting mission: {mission_id}")

        try:
            await self._update_state(DroneState.ARMING)
            await self.mavsdk_drone.action.arm()
            await self._update_state(DroneState.TAKING_OFF)
            await self.mavsdk_drone.action.set_takeoff_altitude(15.0)
            await self.mavsdk_drone.action.takeoff()
            
            async for ls in self.mavsdk_drone.telemetry.landed_state():
                if ls == LandedState.IN_AIR:
                    log.info(f"[{self.drone_id}] Confirmed airborne.")
                    break
                await asyncio.sleep(0.5)

        except ActionError as e:
            await self._send_event("emergency_landing", details={"reason": f"Takeoff failed: {e}"})
            await self._update_state(DroneState.MISSION_FAILED, f"Takeoff failed: {e}")
            self.active_mission_id = None
            return

        try:
            await self._update_state(DroneState.IN_TRANSIT)
            mission_items = [
                MissionItem(
                    wp["lat"], wp["lon"], float(wp["alt_m"]), 15.0, True,
                    float('nan'), float('nan'), MissionItem.CameraAction.NONE,
                    float('nan'), float('nan'), 5.0
                ) for wp in waypoints
            ]
            mission_plan = MissionPlan(mission_items)
            await self.mavsdk_drone.mission.set_return_to_launch_after_mission(False)
            await self.mavsdk_drone.mission.upload_mission(mission_plan)
            await self.mavsdk_drone.mission.start_mission()
        
        except MissionError as e:
            await self._send_event("emergency_landing", details={"reason": f"Mission upload/start failed: {e}"})
            await self._update_state(DroneState.MISSION_FAILED, f"Mission failed: {e}")
            self.active_mission_id = None
            await self.execute_return_to_home()

    async def execute_return_to_home(self):
        if self.current_state in [DroneState.DISCONNECTED_PIXHAWK, DroneState.BOOTING, DroneState.LANDING, DroneState.RETURNING]:
            return
        try:
            await self._update_state(DroneState.RETURNING)
            await self.mavsdk_drone.action.return_to_launch()
        except ActionError as e:
            await self._send_event("emergency_landing", details={"reason": f"RTL failed: {e}"})
            await self._update_state(DroneState.EMERGENCY_LANDING, f"RTL failed: {e}")

    async def run(self):
        await self._update_state(DroneState.BOOTING)
        while True:
            current_run_state = self.current_state
            log.debug(f"[{self.drone_id}] Main loop. State: {current_run_state.name}")
            try:
                if current_run_state in [DroneState.BOOTING, DroneState.DISCONNECTED_PIXHAWK]:
                    await self._connect_to_pixhawk()
                elif current_run_state == DroneState.GETTING_JWT:
                    await self._get_jwt_token()
                elif current_run_state == DroneState.DISCONNECTED_SERVER:
                     if await self._connect_to_server():
                         await self._cancel_all_tasks() 
                         await self._start_task(self._listen_for_server_commands())
                         await self._start_task(self._send_telemetry_loop())
                         await self._start_task(self._process_command_queue())
            except Exception as e:
                log.critical(f"[{self.drone_id}] CRITICAL ERROR in main loop: {e}")
                await self._update_state(DroneState.EMERGENCY_LANDING, f"Main Loop Error: {e}")
                await self._cancel_all_tasks()
            
            await asyncio.sleep(RECONNECT_DELAY_S)

async def main():
    companion = DroneCompanion(
        drone_id=DRONE_ID,
        ws_uri_base=WEBSOCKET_URI_BASE,
        mavlink_conn=MAVLINK_CONNECTION,
        api_token=AUTH_TOKEN
    )
    await companion.run()

if __name__ == "__main__":
    asyncio.run(main())
