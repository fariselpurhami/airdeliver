# file: drone_client/drone-control.py 

import asyncio
import json
import logging
import os
import uuid
import time 
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Dict, Any, Optional, Tuple, List, Set 

import websockets
from mavsdk import System
from mavsdk.action import ActionError
from mavsdk.mission import MissionItem, MissionPlan, MissionError
from mavsdk.telemetry import LandedState, FlightMode, GpsInfo, Battery, Health, Position
from mavsdk.offboard import OffboardError, PositionNedYaw
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, Field, field_validator 

load_dotenv() 

DRONE_ID = os.getenv("DRONE_ID", f"COMPANION-{uuid.uuid4().hex[:6].upper()}")
WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "api")
WEBSOCKET_PORT = os.getenv("WEBSOCKET_PORT", "8000")
WEBSOCKET_URI = os.getenv("WEBSOCKET_URI", f"ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws/drones/")
MAVLINK_CONNECTION = os.getenv("MAVLINK_CONNECTION", "udp://:14540") 
AUTH_TOKEN = os.getenv("AUTH_TOKEN") 
if not AUTH_TOKEN:
            raise ValueError("AUTH_TOKEN environment variable not set.")


TELEMETRY_INTERVAL_S = 2.0
HEARTBEAT_TIMEOUT_S = 30.0 
RECONNECT_DELAY_S = 5.0
DEFAULT_TAKEOFF_ALTITUDE_M = 10.0
DEFAULT_CRUISE_SPEED_M_S = 15.0 
DEFAULT_ARRIVAL_RADIUS_M = 5.0 
PREFLIGHT_MIN_BATTERY_PCT = 60.0
PREFLIGHT_MIN_GPS_SATS = 8
PREFLIGHT_MAX_HDOP = 2.0 
LOW_BATTERY_RETURN_THRESHOLD_PCT = 25.0
LOW_BATTERY_EMERGENCY_THRESHOLD_PCT = 15.0
COMMS_LOSS_TIMEOUT_S = 60.0 

log = logging.getLogger("DroneCompanion")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

class DroneState(Enum):
    BOOTING = auto()
    DISCONNECTED_PIXHAWK = auto()
    CONNECTING_PIXHAWK = auto()
    DISCONNECTED_SERVER = auto()
    CONNECTING_SERVER = auto()
    IDLE = auto()               
    PREFLIGHT_CHECKS = auto()
    READY_FOR_ARMING = auto()   
    ARMING = auto()
    ARMED = auto()              
    TAKING_OFF = auto()
    IN_TRANSIT = auto()         
    PAUSED = auto()     
    APPROACH = auto()           
    DROPPING = auto()       
    RETURNING = auto()          
    LANDING = auto()
    MISSION_COMPLETED = auto()  
    MISSION_FAILED = auto()     
    EMERGENCY_LANDING = auto()  


class CommandMissionWaypoint(BaseModel): lat: float; lon: float; alt_m: float
class CommandMissionPayload(BaseModel): mission_id: str; waypoints: List[CommandMissionWaypoint]; loiter_time_s: Optional[int] = None
class CommandGotoPayload(BaseModel): lat: float; lon: float; alt_m: float
class CommandPayload(BaseModel): action: str; mission: Optional[CommandMissionPayload] = None; goto: Optional[CommandGotoPayload] = None; requires_ack: bool = True
class CommandMessage(BaseModel): type: str; command_id: str; timestamp: datetime; payload: CommandPayload

class DroneCompanion:
    def __init__(self, drone_id: str, ws_uri: str, mavlink_conn: str, token: str):
        self.drone_id = drone_id
        self.ws_uri_base = ws_uri.rstrip('/')
        self.ws_uri = f"{self.ws_uri_base}/{self.drone_id}"
        self.mavlink_conn = mavlink_conn
        self.token = token

        self.mavsdk_drone = System()
        self.current_state = DroneState.BOOTING
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.command_queue = asyncio.Queue()
        self.active_mission_id: Optional[str] = None
        self.last_telemetry: Dict[str, Any] = {}
        self.last_server_comm_time: Optional[datetime] = None
        self._tasks: Set[asyncio.Task] = set()

        log.info(f"[{self.drone_id}] Initializing Companion...")

    async def _start_task(self, coro):
        """Helper to start and track tasks."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard) 
        return task

    async def _cancel_all_tasks(self):
        """Cancel all tracked tasks."""
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
            if self.websocket and self.websocket.open:
                 await self._send_event(f"state_{new_state.name.lower()}", details={"previous_state": old_state, "reason": reason})

    async def _connect_to_pixhawk(self):
        await self._update_state(DroneState.CONNECTING_PIXHAWK)
        log.info(f"[{self.drone_id}] Connecting to Pixhawk: {self.mavlink_conn}")
        await self.mavsdk_drone.connect(system_address=self.mavlink_conn)

        try:
            
            await asyncio.wait_for(self._wait_for_pixhawk_connection(), timeout=30.0)
            log.info(f"[{self.drone_id}] Pixhawk connected!")
            await self._update_state(DroneState.DISCONNECTED_SERVER) 
            return True
        except asyncio.TimeoutError:
            log.error(f"[{self.drone_id}] Timeout waiting for Pixhawk connection.")
            await self._update_state(DroneState.DISCONNECTED_PIXHAWK, "Connection Timeout")
            return False
        except Exception as e:
            log.error(f"[{self.drone_id}] Error connecting to Pixhawk: {e}", exc_info=True)
            await self._update_state(DroneState.DISCONNECTED_PIXHAWK, f"Connection Error: {e}")
            return False

    async def _wait_for_pixhawk_connection(self):
         """Async generator helper to wait for MAVSDK connection."""
         async for state in self.mavsdk_drone.core.connection_state():
            if state.is_connected:
                return

    async def _connect_to_server(self):
        await self._update_state(DroneState.CONNECTING_SERVER)
        log.info(f"[{self.drone_id}] Connecting to WebSocket Server: {self.ws_uri}")
        try:
            self.websocket = await websockets.connect(self.ws_uri, ping_interval=20, ping_timeout=10)
            self.last_server_comm_time = datetime.now(timezone.utc)

            handshake = {
                "type": "connect",
                "drone_id": self.drone_id,
                "token": self.token,
                "meta": {"companion": "mavsdk-v1.x", "firmware": "px4-unknown"} 
            }
            await self.websocket.send(json.dumps(handshake))
            log.info(f"[{self.drone_id}] Handshake sent, waiting for confirmation...")

            response_str = await asyncio.wait_for(self.websocket.recv(), timeout=15.0)
            response = json.loads(response_str)
            self.last_server_comm_time = datetime.now(timezone.utc)

            if response.get("status") == "connected" and response.get("drone_id") == self.drone_id:
                log.info(f"[{self.drone_id}] WebSocket Server connected and authenticated.")
                await self._update_state(DroneState.IDLE) # Connected to both, ready
                return True
            else:
                reason = f"Handshake rejected or invalid response: {response}"
                log.warning(f"[{self.drone_id}] {reason}")
                await self.websocket.close()
                self.websocket = None
                await self._update_state(DroneState.DISCONNECTED_SERVER, reason)
                return False

        except Exception as e:
            reason = f"WebSocket connection failed: {e}"
            log.error(f"[{self.drone_id}] {reason}", exc_info=True)
            if self.websocket:
                await self.websocket.close()
            self.websocket = None
            await self._update_state(DroneState.DISCONNECTED_SERVER, reason)
            return False

    async def _ensure_connection(self) -> bool:
        """Checks both connections and attempts reconnect if necessary."""
        if not self.mavsdk_drone.core.is_connected():
            log.warning(f"[{self.drone_id}] Pixhawk disconnected. Attempting reconnect...")
            await self._update_state(DroneState.DISCONNECTED_PIXHAWK, "Connection Lost")
            await self._cancel_all_tasks() 

            if self.websocket and self.websocket.open:
                await self.websocket.close() 
                self.websocket = None
            return False 

        if not self.websocket or not self.websocket.open:
            log.warning(f"[{self.drone_id}] WebSocket server disconnected. Attempting reconnect...")
            await self._update_state(DroneState.DISCONNECTED_SERVER, "Connection Lost")
            await self._cancel_all_tasks() 
            return False 

        if self.last_server_comm_time and \
           (datetime.now(timezone.utc) - self.last_server_comm_time > timedelta(seconds=HEARTBEAT_TIMEOUT_S)):
            log.error(f"[{self.drone_id}] Server communication timeout ({HEARTBEAT_TIMEOUT_S}s). Closing connection.")
            await self.websocket.close()
            self.websocket = None
            await self._update_state(DroneState.DISCONNECTED_SERVER, "Communication Timeout")
            await self._cancel_all_tasks()
            # Trigger Comms Loss Failsafe?
            await self._start_task(self.failsafe_comms_loss())
            return False

        return True 

    async def _send_message(self, message: dict):
         """Safely send a JSON message to the server."""
         if self.websocket and self.websocket.open:
             try:
                 await self.websocket.send(json.dumps(message, default=str)) 
                 self.last_server_comm_time = datetime.now(timezone.utc) 
             except websockets.exceptions.ConnectionClosed:
                 log.warning(f"[{self.drone_id}] Failed to send message, connection closed.", message_type=message.get("type"))
                 await self._update_state(DroneState.DISCONNECTED_SERVER, "Send Failed")
             except Exception as e:
                  log.error(f"[{self.drone_id}] Error sending message", message_type=message.get("type"), error=str(e))
         else:
             log.warning(f"[{self.drone_id}] Cannot send message, WebSocket not connected.", message_type=message.get("type"))

    async def _send_ack(self, command_id: str, status: str, details: Optional[str] = None):
        ack = {"type": "ack", "command_id": command_id, "drone_id": self.drone_id, "status": status}
        if details: ack["details"] = details 
        await self._send_message(ack)
        log.debug(f"[{self.drone_id}] ACK Sent: {command_id} -> {status}")

    async def _send_event(self, event_type: str, details: Optional[Dict] = None):
        event = {
            "type": "event",
            "drone_id": self.drone_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "event_type": event_type,
                "mission_id": self.active_mission_id,
                "details": details or {}
            }
        }
        await self._send_message(event)
        log.info(f"[{self.drone_id}] Event Sent: {event_type}", details=details)

    async def _listen_for_server_commands(self):
        log.info(f"[{self.drone_id}] Starting Command Listener...")
        while self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING]:
            try:
                if not await self._ensure_connection(): break

                message_str = await asyncio.wait_for(self.websocket.recv(), timeout=HEARTBEAT_TIMEOUT_S)
                self.last_server_comm_time = datetime.now(timezone.utc) 
                message = json.loads(message_str)
                msg_type = message.get("type")

                if msg_type == "command":
                    await self.command_queue.put(message)
                elif msg_type == "pong":
                    log.debug(f"[{self.drone_id}] Pong received")
                else:
                    log.warning(f"[{self.drone_id}] Received unexpected message type", type=msg_type)

            except asyncio.TimeoutError:
                log.warning(f"[{self.drone_id}] Server receive timeout. Sending ping.")
                await self._send_message({"type": "ping"})
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException) as e:
                log.warning(f"[{self.drone_id}] Command listener connection closed: {e}")
                await self._update_state(DroneState.DISCONNECTED_SERVER, "Listener Closed")
                break 
            except json.JSONDecodeError:
                log.warning(f"[{self.drone_id}] Received invalid JSON from server.")
            except Exception as e:
                log.error(f"[{self.drone_id}] Error in command listener", error=str(e), exc_info=True)
                await self._update_state(DroneState.DISCONNECTED_SERVER, f"Listener Error: {e}")
                break
        log.info(f"[{self.drone_id}] Command Listener stopped.")


    async def _send_telemetry_loop(self):
        log.info(f"[{self.drone_id}] Starting Telemetry Loop...")
        while self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING]:
            try:
                if not await self._ensure_connection(): break

                async_tasks = {
                    "position": asyncio.create_task(self.mavsdk_drone.telemetry.position().__aiter__().__anext__()),
                    "velocity": asyncio.create_task(self.mavsdk_drone.telemetry.velocity_ned().__aiter__().__anext__()),
                    "battery": asyncio.create_task(self.mavsdk_drone.telemetry.battery().__aiter__().__anext__()),
                    "flight_mode": asyncio.create_task(self.mavsdk_drone.telemetry.flight_mode().__aiter__().__anext__()),
                    "gps_info": asyncio.create_task(self.mavsdk_drone.telemetry.gps_info().__aiter__().__anext__()),
                    "health": asyncio.create_task(self.mavsdk_drone.telemetry.health().__aiter__().__anext__()),
                    "landed_state": asyncio.create_task(self.mavsdk_drone.telemetry.landed_state().__aiter__().__anext__()),
                }
                await asyncio.wait(async_tasks.values()) 
                pos: Optional[Position] = async_tasks["position"].result()
                vel = async_tasks["velocity"].result()
                bat: Optional[Battery] = async_tasks["battery"].result()
                fm: Optional[FlightMode] = async_tasks["flight_mode"].result()
                gps: Optional[GpsInfo] = async_tasks["gps_info"].result()
                health: Optional[Health] = async_tasks["health"].result()
                ls: Optional[LandedState] = async_tasks["landed_state"].result()

                if not all([pos, vel, bat, fm, gps, health, ls]):
                     log.warning(f"[{self.drone_id}] Failed to get one or more telemetry points.")
                     await asyncio.sleep(TELEMETRY_INTERVAL_S)
                     continue

                battery_pct = int(bat.remaining_percent * 100)
                if battery_pct < LOW_BATTERY_EMERGENCY_THRESHOLD_PCT and self.current_state not in [DroneState.LANDING, DroneState.EMERGENCY_LANDING]:
                     log.critical(f"[{self.drone_id}] EMERGENCY: Battery critically low ({battery_pct}%). Initiating emergency land.")
                     await self._start_task(self.failsafe_emergency_land("Critical Battery"))
                elif battery_pct < LOW_BATTERY_RETURN_THRESHOLD_PCT and self.current_state not in [DroneState.RETURNING, DroneState.LANDING, DroneState.EMERGENCY_LANDING]:
                     log.warning(f"[{self.drone_id}] WARNING: Battery low ({battery_pct}%). Initiating Return to Home.")
                     await self._start_task(self.execute_return_to_home(f"failsafe-lowbat-{uuid.uuid4().hex[:4]}")) 
                flags = []
                if gps.fix_type >= 3: flags.append("gps_locked")
                if health.is_gyrometer_calibration_ok and health.is_accelerometer_calibration_ok: flags.append("imu_ok")
                if health.is_magnetometer_calibration_ok: flags.append("mag_ok")
                if health.is_local_position_ok: flags.append("local_pos_ok")
                if health.is_global_position_ok: flags.append("global_pos_ok")
                if health.is_armable: flags.append("armable")

                current_mav_landed_state = ls.name
                
                if ls == LandedState.ON_GROUND and self.current_state in [DroneState.LANDING, DroneState.RETURNING, DroneState.EMERGENCY_LANDING]:
                     log.info(f"[{self.drone_id}] Detected landing completion via telemetry.")
                     final_state = DroneState.IDLE
                     if self.active_mission_id:
                         final_state = DroneState.MISSION_COMPLETED if self.current_state != DroneState.EMERGENCY_LANDING else DroneState.MISSION_FAILED
                     await self._update_state(final_state, "Landed")
                     self.active_mission_id = None 


                telemetry_payload = {
                    "lat": pos.latitude_deg, "lon": pos.longitude_deg, "alt_m": pos.relative_altitude_m,
                    "ground_speed_m_s": (vel.north_m_s**2 + vel.east_m_s**2)**0.5,
                    "battery_pct": battery_pct, "mission_id": self.active_mission_id,
                    "flight_mode": fm.name, "flags": flags
                }
                telemetry_msg = { 
                    "type": "telemetry",
                    "drone_id": self.drone_id,
                    "timestamp": datetime.now(timezone.utc),
                    "payload": telemetry_payload
                }
                self.last_telemetry = telemetry_msg 

                await self._send_message(telemetry_msg)

            except StopAsyncIteration:
                log.warning(f"[{self.drone_id}] Telemetry stream ended unexpectedly. Will retry.")
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException):
                log.warning(f"[{self.drone_id}] Telemetry loop connection closed.")
                await self._update_state(DroneState.DISCONNECTED_SERVER, "Telemetry Send Failed")
                break 
            except Exception as e:
                log.error(f"[{self.drone_id}] Error in telemetry loop", error=str(e), exc_info=True)
            finally:
                
                 if self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING]:
                     await asyncio.sleep(TELEMETRY_INTERVAL_S) 
                 else:
                      break 

        log.info(f"[{self.drone_id}] Telemetry Loop stopped.")


    async def _process_command_queue(self):
        log.info(f"[{self.drone_id}] Starting Command Processor...")
        while self.current_state not in [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER, DroneState.BOOTING]:
            command_msg = await self.command_queue.get()
            command_id = "unknown" 
            requires_ack = True 
            try:
                
                if not isinstance(command_msg, dict) or command_msg.get("type") != "command":
                     log.warning("Dequeued invalid message", message=command_msg)
                     continue

                command_id = command_msg.get("command_id", f"cmd-nokey-{uuid.uuid4().hex[:4]}")
                requires_ack = command_msg.get("payload", {}).get("requires_ack", True) # Default true

                command = CommandMessage.model_validate(command_msg)
                action = command.payload.action
                payload = command.payload 

                log.info(f"Processing command", action=action, command_id=command_id)

                if requires_ack: await self._send_ack(command_id, "accepted")

                success = False
                error_msg = "Action not implemented or invalid state"

                if not self.mavsdk_drone.core.is_connected():
                     error_msg = "Pixhawk connection lost before execution"
                     log.error(error_msg, command_id=command_id)

                elif action == "start_mission" and payload.mission:
                    success, error_msg = await self.execute_mission(payload.mission, command_id)
                elif action == "return_to_home":
                    success, error_msg = await self.execute_return_to_home(command_id)
                elif action == "goto" and payload.goto:
                     success, error_msg = await self.execute_goto(payload.goto.lat, payload.goto.lon, payload.goto.alt_m, command_id)
                elif action == "release_payload":
                    success, error_msg = await self.execute_release_payload(command_id)
                elif action == "abort":
                     success, error_msg = await self.execute_abort(command_id)
                elif action == "pause":
                     success, error_msg = await self.execute_pause_mission(command_id)
                elif action == "resume":
                     success, error_msg = await self.execute_resume_mission(command_id)
        

                else:
                    error_msg = f"Unknown or invalid action: {action}"
                    log.warning(error_msg, command_id=command_id)

                if requires_ack:
                    final_status = "completed" if success else f"failed:{error_msg or 'Unknown reason'}"
                    await self._send_ack(command_id, final_status)

            except ValidationError as e:
                 reason = f"Invalid command format: {e.errors()}"
                 log.warning(reason, command_id=command_id, raw_command=command_msg)
                 if requires_ack: await self._send_ack(command_id, f"rejected:{reason}")
            except Exception as e:
                 reason = f"Error processing command: {e}"
                 log.error(reason, command_id=command_id, exc_info=True)
                 if requires_ack: await self._send_ack(command_id, f"failed:{reason}")
            finally:
                self.command_queue.task_done()
        log.info(f"[{self.drone_id}] Command Processor stopped.")

    async def run_preflight_checks(self) -> Tuple[bool, str]:
         await self._update_state(DroneState.PREFLIGHT_CHECKS)
         log.info(f"[{self.drone_id}] Running preflight checks...")
         try:
              
              await asyncio.sleep(1)
              bat: Optional[Battery] = await self.mavsdk_drone.telemetry.battery().__aiter__().__anext__()
              gps: Optional[GpsInfo] = await self.mavsdk_drone.telemetry.gps_info().__aiter__().__anext__()
              health: Optional[Health] = await self.mavsdk_drone.telemetry.health().__aiter__().__anext__()

              failures = []
              if not bat or int(bat.remaining_percent * 100) < PREFLIGHT_MIN_BATTERY_PCT:
                   failures.append(f"Battery low ({int(bat.remaining_percent*100) if bat else 'N/A'}% < {PREFLIGHT_MIN_BATTERY_PCT}%)")
              if not gps or gps.fix_type < 3:
                   failures.append(f"GPS fix inadequate (fix: {gps.fix_type if gps else 'N/A'} < 3)")
              if not gps or gps.num_satellites < PREFLIGHT_MIN_GPS_SATS:
                   failures.append(f"Insufficient GPS satellites ({gps.num_satellites if gps else 'N/A'} < {PREFLIGHT_MIN_GPS_SATS})")
              
              if not health or not health.is_armable:
                   failures.append("System not armable (check health flags)")

              if not failures:
                   log.info(f"[{self.drone_id}] Preflight checks passed.")
                   await self._send_event("preflight_ok")
                   await self._update_state(DroneState.READY_FOR_ARMING)
                   return True, "Checks Passed"
              else:
                   reason = ", ".join(failures)
                   log.warning(f"[{self.drone_id}] Preflight checks failed", failures=failures)
                   await self._send_event("preflight_failed", details={"reasons": failures})
                   await self._update_state(DroneState.IDLE, f"Preflight Failed: {reason}")
                   return False, reason

         except Exception as e:
              reason = f"Exception during preflight checks: {e}"
              log.error(f"[{self.drone_id}] {reason}", exc_info=True)
              await self._send_event("preflight_failed", details={"reasons": [reason]})
              await self._update_state(DroneState.IDLE, reason)
              return False, reason

    async def execute_mission(self, mission_payload: CommandMissionPayload, command_id: str) -> Tuple[bool, Optional[str]]:
        if self.current_state not in [DroneState.IDLE]:
            return False, f"Invalid state: {self.current_state.name}"

        mission_id = mission_payload.mission_id
        waypoints = mission_payload.waypoints
        if not mission_id or not waypoints:
            return False, "Missing mission_id or waypoints"

        checks_ok, checks_reason = await self.run_preflight_checks()
        if not checks_ok: return False, f"Preflight Failed: {checks_reason}"

        self.active_mission_id = mission_id
        log.info(f"[{self.drone_id}] Starting mission", mission_id=mission_id)

        try:
            await self._update_state(DroneState.ARMING)
            log.info(f"[{self.drone_id}] Arming...")
            await self.mavsdk_drone.action.arm()
            async for armed in self.mavsdk_drone.telemetry.armed():
                if armed:
                    log.info(f"[{self.drone_id}] Confirmed armed.")
                    await self._update_state(DroneState.ARMED)
                    break 
                await asyncio.sleep(0.2)
            
        except ActionError as e:
            reason = f"Arming failed: {e}"
            log.error(f"[{self.drone_id}] {reason}")
            await self._update_state(DroneState.IDLE, reason)
            self.active_mission_id = None
            return False, reason

        
        try:
            await self._update_state(DroneState.TAKING_OFF)
            takeoff_alt = DEFAULT_TAKEOFF_ALTITUDE_M
            log.info(f"[{self.drone_id}] Setting takeoff altitude to {takeoff_alt}m...")
            await self.mavsdk_drone.action.set_takeoff_altitude(float(takeoff_alt))
            log.info(f"[{self.drone_id}] Commanding Takeoff...")
            await self.mavsdk_drone.action.takeoff()
            await self._send_event("takeoff")
            log.info(f"[{self.drone_id}] Takeoff command sent. Waiting for airborne state...")
            
            async for ls in self.mavsdk_drone.telemetry.landed_state():
                if ls == LandedState.IN_AIR:
                    log.info(f"[{self.drone_id}] Confirmed airborne.")
                    break
                await asyncio.sleep(0.5)

        except ActionError as e:
            reason = f"Takeoff failed: {e}"; log.error(f"[{self.drone_id}] {reason}")
            await self.mavsdk_drone.action.disarm(); await self._update_state(DroneState.IDLE, reason)
            self.active_mission_id = None; return False, reason
        except Exception as e:
            reason = f"Unexpected takeoff error: {e}"; log.error(f"[{self.drone_id}] {reason}", exc_info=True)
            await self._update_state(DroneState.EMERGENCY_LANDING, reason); self.active_mission_id = None; return False, reason

        
        try:
            await self._update_state(DroneState.IN_TRANSIT)
            mission_items = [
                MissionItem(
                    wp.lat, wp.lon, float(wp.alt_m), DEFAULT_CRUISE_SPEED_M_S, True,
                    float('nan'), float('nan'), MissionItem.CameraAction.NONE,
                    float('nan'), float('nan'), DEFAULT_ARRIVAL_RADIUS_M
                ) for wp in waypoints
            ]
            mission_plan = MissionPlan(mission_items)
            log.info(f"[{self.drone_id}] Uploading mission plan ({len(mission_items)} items)...")
            await self.mavsdk_drone.mission.set_return_to_launch_after_mission(False)
            await self.mavsdk_drone.mission.upload_mission(mission_plan)
            log.info(f"[{self.drone_id}] Mission uploaded. Starting...")
            await self.mavsdk_drone.mission.start_mission()
            log.info(f"[{self.drone_id}] Mission started. Monitoring progress...")

            await self._start_task(self._monitor_mission_progress())
        
            return True, "Mission started, monitoring in background"

        
        except MissionError as e:
            reason = f"Mission upload/start failed: {e}"; log.error(f"[{self.drone_id}] {reason}")
            await self._start_task(self.execute_return_to_home(f"failsafe-missionstart-{command_id[:8]}"))
            await self._update_state(DroneState.MISSION_FAILED, reason); self.active_mission_id = None; return False, reason
        except ActionError as e: # Catch arming/takeoff related errors if they happen here
            reason = f"Action error during mission start sequence: {e}"; log.error(f"[{self.drone_id}] {reason}")
            await self._start_task(self.execute_return_to_home(f"failsafe-missionstart-{command_id[:8]}"))
            await self._update_state(DroneState.MISSION_FAILED, reason); self.active_mission_id = None; return False, reason
        except Exception as e:
            reason = f"Unexpected mission start error: {e}"; log.error(f"[{self.drone_id}] {reason}", exc_info=True)
            await self._start_task(self.failsafe_emergency_land(reason)); await self._update_state(DroneState.EMERGENCY_LANDING, reason)
            self.active_mission_id = None; return False, reason


    async def _monitor_mission_progress(self):
        """Background task to monitor mission state."""
        log.info(f"[{self.drone_id}] Mission monitor started.", mission_id=self.active_mission_id)
        try:
            async for mission_progress in self.mavsdk_drone.mission.mission_progress():
                log.info(f"Mission progress: {mission_progress.current}/{mission_progress.total}", mission_id=self.active_mission_id)
                if self.current_state != DroneState.IN_TRANSIT:
                    log.warning(f"[{self.drone_id}] Mission monitor running but state is {self.current_state.name}. Stopping monitor.")
                    return 

                if mission_progress.current == mission_progress.total and mission_progress.total > 0:
                    log.info(f"[{self.drone_id}] Reached final mission item.")
                    
                    if await self.mavsdk_drone.mission.is_mission_finished():
                        log.info(f"[{self.drone_id}] MAVSDK confirms mission finished.")
                    
                        await self._update_state(DroneState.RETURNING, "Mission Finished, expecting RTL/Land")
                    else:
                    
                        log.info(f"[{self.drone_id}] Reached last WP, awaiting further commands or PX4 action.")
                        await self._update_state(DroneState.APPROACH) 
                    return 

            log.warning(f"[{self.drone_id}] Mission progress stream ended unexpectedly.")
            if self.mavsdk_drone.core.is_connected() and self.active_mission_id:
            
                await self._update_state(DroneState.MISSION_FAILED, "Progress Stream Ended")
                await self._start_task(self.execute_return_to_home(f"failsafe-progress-end-{self.active_mission_id[:8]}"))

        except Exception as e:
            log.error(f"[{self.drone_id}] Error in mission monitor", error=str(e), exc_info=True)
            if self.active_mission_id: 
                await self._update_state(DroneState.MISSION_FAILED, f"Monitor Error: {e}")
                await self._start_task(self.execute_return_to_home(f"failsafe-monitor-err-{self.active_mission_id[:8]}"))
        finally:
            log.info(f"[{self.drone_id}] Mission monitor stopped.", mission_id=self.active_mission_id)
        

    async def execute_goto(self, lat: float, lon: float, alt_m: float, command_id: str) -> Tuple[bool, Optional[str]]:
         if self.current_state not in [DroneState.IDLE, DroneState.IN_TRANSIT, DroneState.PAUSED, DroneState.ARMED, DroneState.TAKING_OFF]:
              return False, f"Cannot goto from state {self.current_state.name}"
         try:
              log.info(f"[{self.drone_id}] Executing goto: LAT={lat}, LON={lon}, ALT={alt_m}")
              await self._update_state(DroneState.IN_TRANSIT)
              await self.mavsdk_drone.action.goto_location(lat, lon, alt_m, 0) 
              log.info(f"[{self.drone_id}] Goto command issued. Monitoring arrival is complex, assuming success for now.")
              
              await asyncio.sleep(5) 
              if self.current_state == DroneState.IN_TRANSIT: 
                  await self._update_state(DroneState.IDLE)
              return True, None
         except ActionError as e:
              reason = f"Goto failed: {e}"
              log.error(f"[{self.drone_id}] {reason}")
              await self._update_state(DroneState.IDLE) 
              return False, reason
         except Exception as e:
              reason = f"Unexpected error during goto: {e}"
              log.error(f"[{self.drone_id}] {reason}", exc_info=True)
              await self._start_task(self.failsafe_emergency_land(reason))
              await self._update_state(DroneState.EMERGENCY_LANDING, reason)
              return False, reason

    async def execute_return_to_home(self, command_id: str) -> Tuple[bool, Optional[str]]:
        if self.current_state in [DroneState.DISCONNECTED_PIXHAWK, DroneState.CONNECTING_PIXHAWK,
                                  DroneState.DISCONNECTED_SERVER, DroneState.CONNECTING_SERVER,
                                  DroneState.BOOTING, DroneState.LANDING, DroneState.RETURNING,
                                  DroneState.EMERGENCY_LANDING]:
            return False, f"Cannot RTL from state {self.current_state.name}"
        try:
            log.info(f"[{self.drone_id}] Executing Return to Home (RTL)...")
            await self._update_state(DroneState.RETURNING)
            try:
                if await self.mavsdk_drone.mission.is_mission_active():
                    await self.mavsdk_drone.mission.pause_mission()
                    await self.mavsdk_drone.mission.clear_mission()
                    log.info(f"[{self.drone_id}] Ongoing mission cleared before RTL.")
            except Exception as e:
                 log.warning(f"[{self.drone_id}] Could not clear mission before RTL: {e}")

            await self.mavsdk_drone.action.return_to_launch()
            log.info(f"[{self.drone_id}] RTL command issued. Monitoring landing.")
            async for landed_state in self.mavsdk_drone.telemetry.landed_state():
                if landed_state == LandedState.ON_GROUND:
                    log.info(f"[{self.drone_id}] RTL completed, landed.")
                    await self._send_event("landed", details={"reason": "RTL"})
            
                    if self.active_mission_id:
                         await self._update_state(DroneState.MISSION_FAILED, "RTL Triggered")
                    else:
                         await self._update_state(DroneState.IDLE) 
                    self.active_mission_id = None
            
                    await self.mavsdk_drone.action.disarm()
                    log.info(f"[{self.drone_id}] Disarmed after RTL landing.")
                    return True, None
            
            log.warning(f"[{self.drone_id}] RTL monitoring ended without confirming ON_GROUND state.")
            await self._update_state(DroneState.IDLE) 
            return True, "RTL initiated, landing unconfirmed"
        except ActionError as e:
            reason = f"RTL failed: {e}"
            log.error(f"[{self.drone_id}] {reason}")
            await self._update_state(DroneState.EMERGENCY_LANDING, reason)
            return False, reason
        except Exception as e:
              reason = f"Unexpected error during RTL: {e}"
              log.error(f"[{self.drone_id}] {reason}", exc_info=True)
              await self._start_task(self.failsafe_emergency_land(reason))
              await self._update_state(DroneState.EMERGENCY_LANDING, reason)
              return False, reason

    async def execute_release_payload(self, command_id: str) -> Tuple[bool, Optional[str]]:
        if self.current_state not in [DroneState.APPROACH, DroneState.IN_TRANSIT, DroneState.PAUSED]: 
             return False, f"Cannot release payload from state {self.current_state.name}"

        log.info(f"[{self.drone_id}] Executing payload release...")
        await self._update_state(DroneState.DROPPING)
        release_success = False
        error_details = "Simulation only"
        try:
            
            log.info(f"[{self.drone_id}] SIMULATING payload release hardware interaction...")
            await asyncio.sleep(2.0) 
            release_success = True 
            error_details = "Simulated Success"
        

            if release_success:
                log.info(f"[{self.drone_id}] Payload release confirmed.")
                await self._send_event("payload_dropped", details={"method": "servo", "success": True})
                await self._update_state(DroneState.IN_TRANSIT) 
                return True, None
            else:
                reason = "Payload release failed confirmation"
                log.warning(f"[{self.drone_id}] {reason}")
                await self._send_event("payload_dropped", details={"method": "servo", "success": False, "reason": error_details})
                
                await self._update_state(DroneState.IN_TRANSIT) 
                return False, reason

        except Exception as e:
            reason = f"Payload release exception: {e}"
            log.error(f"[{self.drone_id}] {reason}", exc_info=True)
            await self._send_event("payload_dropped", details={"method": "servo", "success": False, "error": str(e)})
            await self._start_task(self.failsafe_emergency_land(reason))
            await self._update_state(DroneState.EMERGENCY_LANDING, reason)
            return False, reason

    async def execute_abort(self, command_id: str) -> Tuple[bool, Optional[str]]:
        """Emergency stop - potentially dangerous. Use RTL for safe return."""
        log.warning(f"[{self.drone_id}] Received ABORT command. Attempting DISARM immediately!")
        try:
             
             await self.mavsdk_drone.action.kill() 
             await self._update_state(DroneState.MISSION_FAILED, "Aborted by Command (Kill)")
             self.active_mission_id = None
             await self._send_event("emergency_landing", details={"reason": "Abort command (Kill)"})
             return True, None
        except ActionError as e:
             reason = f"Abort (Kill) failed: {e}"
             log.error(f"[{self.drone_id}] {reason}")
        
             await self._update_state(DroneState.EMERGENCY_LANDING, reason)
             return False, reason

    async def execute_pause_mission(self, command_id: str) -> Tuple[bool, Optional[str]]:
        if self.current_state != DroneState.IN_TRANSIT:
             return False, f"Can only pause when IN_TRANSIT, current state: {self.current_state.name}"
        try:
             log.info(f"[{self.drone_id}] Pausing mission...")
             await self.mavsdk_drone.mission.pause_mission()
             await self._update_state(DroneState.PAUSED)
             log.info(f"[{self.drone_id}] Mission paused.")
             return True, None
        except (MissionError, ActionError) as e:
             reason = f"Failed to pause mission: {e}"
             log.error(f"[{self.drone_id}] {reason}")
            
             return False, reason

    async def execute_resume_mission(self, command_id: str) -> Tuple[bool, Optional[str]]:
        if self.current_state != DroneState.PAUSED:
             return False, f"Can only resume when PAUSED, current state: {self.current_state.name}"
        try:
             log.info(f"[{self.drone_id}] Resuming mission...")
             await self.mavsdk_drone.mission.start_mission() 
             await self._update_state(DroneState.IN_TRANSIT)
             log.info(f"[{self.drone_id}] Mission resumed.")
             return True, None
        except (MissionError, ActionError) as e:
             reason = f"Failed to resume mission: {e}"
             log.error(f"[{self.drone_id}] {reason}")
             return False, reason


    async def failsafe_comms_loss(self):
        
        if self.current_state in [DroneState.ARMING, DroneState.ARMED, DroneState.TAKING_OFF,
                                 DroneState.IN_TRANSIT, DroneState.APPROACH, DroneState.DROPPING,
                                 DroneState.PAUSED, DroneState.RETURNING, DroneState.LANDING]:
            log.warning(f"[{self.drone_id}] FAILSAFE: Server Communication lost. Waiting {COMMS_LOSS_TIMEOUT_S}s before RTL.")
            await asyncio.sleep(COMMS_LOSS_TIMEOUT_S)

            if self.current_state == DroneState.DISCONNECTED_SERVER:
                log.error(f"[{self.drone_id}] FAILSAFE: Still disconnected. Triggering RTL.")
                await self.execute_return_to_home(f"failsafe-commsloss-{uuid.uuid4().hex[:4]}")
        else:
            log.info(f"[{self.drone_id}] Comms lost but drone state ({self.current_state.name}) is safe. No failsafe action.")

    async def failsafe_emergency_land(self, reason: str):
    
        if self.current_state not in [DroneState.EMERGENCY_LANDING, DroneState.MISSION_COMPLETED, DroneState.MISSION_FAILED]:
            original_state = self.current_state.name
            log.critical(f"[{self.drone_id}] FAILSAFE: Triggering Emergency Land from state {original_state}. Reason: {reason}")
            await self._cancel_all_tasks() 
            await self._update_state(DroneState.EMERGENCY_LANDING, reason)
            await self._send_event("emergency_landing", details={"reason": reason, "previous_state": original_state})
            try:
                log.info(f"[{self.drone_id}] Attempting controlled LAND...")
                await self.mavsdk_drone.action.land()
                land_timeout = 120.0 
                start_time = time.monotonic()
                async for landed_state in self.mavsdk_drone.telemetry.landed_state():
                    if landed_state == LandedState.ON_GROUND:
                        log.info(f"[{self.drone_id}] Emergency Land completed (on ground). Disarming.")
                        await self.mavsdk_drone.action.disarm()
                        log.info(f"[{self.drone_id}] Disarmed after emergency landing.")
                        return 
                    if time.monotonic() - start_time > land_timeout:
                        log.error(f"[{self.drone_id}] Timeout waiting for emergency land confirmation.")
                        break 

            except ActionError as e:
                log.error(f"[{self.drone_id}] Emergency Land command failed: {e}. Attempting KILL!")
            except Exception as e:
                log.error(f"[{self.drone_id}] Error during emergency land", error=str(e), exc_info=True)

            log.critical(f"[{self.drone_id}] Emergency Land failed or timed out. Attempting KILL!")
            try:
                await self.mavsdk_drone.action.kill()
                log.info(f"[{self.drone_id}] KILL command issued.")
            except ActionError as kill_e:
                log.critical(f"[{self.drone_id}] KILL command ALSO FAILED: {kill_e}")

    async def run(self):
        await self._update_state(DroneState.BOOTING)
        while True:
            current_run_state = self.current_state
            log.debug(f"[{self.drone_id}] Main loop iteration. State: {current_run_state.name}")
            try:
                if current_run_state in [DroneState.BOOTING, DroneState.DISCONNECTED_PIXHAWK]:
                    if await self._connect_to_pixhawk():
                        continue 
                elif current_run_state == DroneState.DISCONNECTED_SERVER:
                    
                     if await self._connect_to_server():
                         
                         log.info(f"[{self.drone_id}] Starting operational tasks...")
                         await self._cancel_all_tasks() 
                         await self._start_task(self._listen_for_server_commands())
                         await self._start_task(self._send_telemetry_loop())
                         await self._start_task(self._process_command_queue())
                         continue 
                     else:
                        
                          pass 

                elif current_run_state not in [DroneState.CONNECTING_PIXHAWK, DroneState.CONNECTING_SERVER]:
                
                     pass 

            except Exception as e:
                log.critical(f"[{self.drone_id}] CRITICAL ERROR in main loop", error=str(e), exc_info=True)
                await self._update_state(DroneState.EMERGENCY_LANDING, f"Main Loop Error: {e}")
                await self._cancel_all_tasks()
                await self.failsafe_emergency_land(f"Main Loop Error: {e}")
            
                log.critical(f"[{self.drone_id}] Exiting main loop after critical error.")
                break

            
            await asyncio.sleep(RECONNECT_DELAY_S if current_run_state in
                                [DroneState.DISCONNECTED_PIXHAWK, DroneState.DISCONNECTED_SERVER] else 1.0)


async def main():
    companion = DroneCompanion(
        drone_id=DRONE_ID,
        ws_uri=WEBSOCKET_URI,
        mavlink_conn=MAVLINK_CONNECTION,
        token=AUTH_TOKEN
    )
    try:
        await companion.run()
    finally:
        
         await companion._cancel_all_tasks()
         log.info(f"[{companion.drone_id}] Main task finished or cancelled.")


if __name__ == "__main__":
    log.info("Starting Drone Companion...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Companion stopped by user.")
    except Exception as e:
         log.critical("Unhandled exception in main execution", error=str(e), exc_info=True)
