import asyncio
import signal
import sys
import json
import logging
import datetime
from typing import Optional, Dict
from enum import Enum, auto
from dataclasses import dataclass

# -----------------------------------------------------------------------------
# 1. OBSERVABILITY LAYER (Structured Logging)
# -----------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "MissionControl",
            "event": record.getMessage(), # We treat message as event name
            "module": record.module,
        }
        if hasattr(record, "props"):
            log_obj.update(record.props)
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("MissionLogger")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def log(event: str, level: str = "INFO", **kwargs):
    extra = {"props": kwargs}
    if level == "INFO": logger.info(event, extra=extra)
    elif level == "ERROR": logger.error(event, extra=extra)
    elif level == "CRITICAL": logger.critical(event, extra=extra)

# -----------------------------------------------------------------------------
# 2. SYSTEM ARCHITECTURE
# -----------------------------------------------------------------------------
class MissionPhase(Enum):
    INIT = auto()
    CONNECTING = auto()
    ARMING = auto()
    TAKING_OFF = auto()
    HOVERING = auto()
    LANDING = auto()
    COMPLETED = auto()
    ABORTED = auto()

@dataclass
class MissionConfig:
    BIND_ADDRESS: str = "udp://:14540"
    TAKEOFF_ALTITUDE_M: float = 10.0
    HOVER_DURATION_S: int = 5
    CONNECTION_TIMEOUT_S: int = 30

CONFIG = MissionConfig()

try:
    from mavsdk import System
    from mavsdk.action import ActionError
except ImportError:
    log("dependency_missing", level="CRITICAL", library="mavsdk")
    sys.exit(1)

class MissionController:
    """
    Enterprise Flight Control Service.
    Manages the lifecycle of a single drone mission with strict state transitions.
    """
    def __init__(self):
        self._drone = System()
        self._phase = MissionPhase.INIT
        self._shutdown_event = asyncio.Event()

    async def execute(self):
        """Main execution pipeline."""
        log("system_online", config=CONFIG.__dict__)
        
        try:
            # Phase 1: Uplink
            await self._transition(MissionPhase.CONNECTING)
            await self._establish_uplink()

            # Phase 2: Arm
            await self._transition(MissionPhase.ARMING)
            await self._drone.action.arm()
            log("engines_armed")

            # Phase 3: Takeoff
            await self._transition(MissionPhase.TAKING_OFF)
            await self._drone.action.takeoff()
            # We assume takeoff is async; in prod we would monitor altitude here
            log("takeoff_command_sent", target_alt=CONFIG.TAKEOFF_ALTITUDE_M)

            # Phase 4: Hover (Mission Logic)
            await self._transition(MissionPhase.HOVERING)
            # Start a sidecar task to monitor altitude while we wait
            monitor_task = asyncio.create_task(self._monitor_telemetry())
            
            await asyncio.sleep(CONFIG.HOVER_DURATION_S)
            monitor_task.cancel() # Stop monitoring

            # Phase 5: Return
            await self._transition(MissionPhase.LANDING)
            await self._drone.action.land()
            log("landing_command_sent")
            
            # Wait for disarm (touchdown)
            await self._wait_for_disarm()

            await self._transition(MissionPhase.COMPLETED)
            log("mission_success")

        except Exception as e:
            log("mission_critical_failure", level="CRITICAL", error=str(e), phase=self._phase.name)
            await self._emergency_procedure()
        finally:
            await self._cleanup()

    async def _transition(self, new_phase: MissionPhase):
        log("phase_transition", previous=self._phase.name, current=new_phase.name)
        self._phase = new_phase

    async def _establish_uplink(self):
        log("initiating_handshake", address=CONFIG.BIND_ADDRESS)
        # Binds to the port to receive packets from the Docker Bridge
        await self._drone.connect(system_address=CONFIG.BIND_ADDRESS)

        log("waiting_for_heartbeat", timeout=CONFIG.CONNECTION_TIMEOUT_S)
        async for state in self._drone.core.connection_state():
            if state.is_connected:
                log("uplink_established")
                return
            
    async def _monitor_telemetry(self):
        """Sidecar process: Logs altitude every second during flight."""
        try:
            async for position in self._drone.telemetry.position():
                log("telemetry_update", 
                    alt_rel=round(position.relative_altitude_m, 2),
                    lat=position.latitude_deg,
                    lon=position.longitude_deg
                )
                await asyncio.sleep(2) # Rate limit logs
        except asyncio.CancelledError:
            pass

    async def _wait_for_disarm(self):
        """Blocks until the drone reports it is on the ground."""
        log("waiting_for_touchdown")
        async for in_air in self._drone.telemetry.in_air():
            if not in_air:
                log("touchdown_confirmed")
                return

    async def _emergency_procedure(self):
        """Failsafe: Attempts to land if airborne."""
        if self._phase in [MissionPhase.TAKING_OFF, MissionPhase.HOVERING]:
            log("initiating_emergency_landing", level="ERROR")
            try:
                await self._drone.action.land()
            except:
                log("emergency_landing_failed", level="CRITICAL")

    async def _cleanup(self):
        log("system_shutdown")

# -----------------------------------------------------------------------------
# 3. ENTRY POINT
# -----------------------------------------------------------------------------
async def main():
    controller = MissionController()
    
    # Graceful Shutdown for K8s
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(controller._emergency_procedure()))

    await controller.execute()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
