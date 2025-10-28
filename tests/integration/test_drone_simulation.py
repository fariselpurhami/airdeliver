# file: tests/integration/test_drone_simulation.py (Improved)
import subprocess
import time
import httpx
import json
import uuid
import pytest
import asyncio
import logging # Added logging
from datetime import datetime, timezone

# --- Logging Setup ---
log = logging.getLogger("IntegrationTest")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not log.hasHandlers():
    log.addHandler(handler)

DOCKER_COMPOSE_FILES = "-f docker-compose.yml -f docker-compose.drone.yml"
API_BASE_URL = "http://localhost:8000" # Main API
WS_INTERNAL_BASE_URL = f"{API_BASE_URL}/ws/internal" # WebSocket internal commands

# Fixture to manage docker compose lifecycle
@pytest.fixture(scope="module", autouse=True)
def run_simulation_stack():
    log.info("Setting up simulation stack...")
    try:
        # Use capture_output=True to hide logs unless test fails
        subprocess.run(f"docker compose {DOCKER_COMPOSE_FILES} down -v --remove-orphans", shell=True, check=True, capture_output=True, text=True)
        # Run build and up, capture output
        up_result = subprocess.run(f"docker compose {DOCKER_COMPOSE_FILES} up --build -d", shell=True, check=True, capture_output=True, text=True)
        log.info(up_result.stdout)
        log.error(up_result.stderr)
        
        log.info("Waiting for services to stabilize...")
        # Improved wait: Poll health endpoints
        wait_for_service(f"{API_BASE_URL}/ws/health", expected_status="ok", timeout=120)
        # Add wait/check for companion readiness if it has a health endpoint
        # wait_for_service("http://localhost:8080/health", timeout=60) # Example
        log.info("Simulation stack ready.")
        yield
    except subprocess.CalledProcessError as e:
        log.error("Failed to set up Docker Compose stack:")
        log.error(f"STDOUT: {e.stdout}")
        log.error(f"STDERR: {e.stderr}")
        pytest.fail(f"Docker Compose setup failed: {e.stderr}")
    finally:
        log.info("Tearing down simulation stack...")
        down_result = subprocess.run(f"docker compose {DOCKER_COMPOSE_FILES} down -v --remove-orphans", shell=True, check=True, capture_output=True, text=True)
        log.debug(down_result.stdout)
        log.debug(down_result.stderr)

def wait_for_service(url: str, expected_status: str | None = None, timeout: int = 60):
    """Polls a health endpoint until it's ready or times out."""
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code == 200:
                if expected_status is None or response.json().get("status") == expected_status:
                    log.info(f"Service at {url} is ready.")
                    return True
                else:
                    log.debug(f"Service at {url} returned status: {response.json().get('status')}")
            else:
                log.debug(f"Service at {url} returned HTTP status: {response.status_code}")
        except httpx.RequestError as e:
            log.debug(f"Waiting for service at {url}: {e}")
        time.sleep(2)
    pytest.fail(f"Service at {url} did not become ready within {timeout} seconds.")


@pytest.mark.asyncio
async def test_simulated_mission_end_to_end(run_simulation_stack):
    drone_id = "SIM-001"
    mission_id = f"m-integ-{uuid.uuid4().hex[:6]}"
    command_id = f"cmd-integ-{uuid.uuid4().hex[:6]}"

    # Define a simple mission
    mission_payload_data = {
        "action": "start_mission",
        "mission": {
            "mission_id": mission_id,
            "waypoints": [
                # Coordinates relative to SITL start (~34.0522, -118.2437)
                {"lat": 34.0530, "lon": -118.2440, "alt_m": 10.0},
                {"lat": 34.0535, "lon": -118.2445, "alt_m": 12.0},
                {"lat": 34.0530, "lon": -118.2450, "alt_m": 10.0}, # Waypoint near drop/finish
            ]
        },
        "requires_ack": True
    }
    command_message = {
        "type": "command", "command_id": command_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": mission_payload_data
    }

    # 1. Send command via internal API
    log.info(f"Sending mission command {command_id} to {drone_id}...")
    send_url = f"{WS_INTERNAL_BASE_URL}/send_command/{drone_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(send_url, json=command_message)
            response.raise_for_status() # Raise exception for 4xx/5xx
            log.info(f"Send command response: {response.status_code}, {response.text}")
            assert response.status_code == 202
            # Check for specific status (might vary based on implementation)
            assert response.json()["status"] in ["command_accepted", "pending_send"] 
        except httpx.HTTPStatusError as e:
            pytest.fail(f"Failed to send command: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            pytest.fail(f"Failed to connect to send command endpoint: {e}")


    # 2. Poll for ACK and Mission Completion (Improved Polling)
    max_wait_time = 180 # seconds
    poll_interval = 5   # seconds
    start_poll_time = time.monotonic()
    mission_completed = False
    ack_status = None

    log.info(f"Polling for ACK and mission completion (max {max_wait_time}s)...")
    while time.monotonic() - start_poll_time < max_wait_time:
        # Check ACK status (assuming Redis is used by WS server)
        # This requires a way to query Redis or an API endpoint for command status
        # Example using Redis directly (needs redis library installed for test)
        # try:
        #     import redis
        #     r = redis.Redis(host='localhost', port=6379, decode_responses=True) # Assumes redis is on localhost:6379
        #     ack_status = r.get(f"command_status:{command_id}")
        #     log.debug(f"Command {command_id} ACK status: {ack_status}")
        #     if ack_status and 'failed' in ack_status:
        #         pytest.fail(f"Command failed with status: {ack_status}")
        # except Exception as e:
        #     log.warning(f"Could not check Redis for ACK status: {e}")

        # Check Mission Status via API (Assuming endpoint exists)
        # THIS IS A PLACEHOLDER - Requires a GET /api/v1/missions/{id} endpoint in your API
        try:
            # Assuming an endpoint like /api/v1/missions/{mission_id} exists
            mission_status_url = f"{API_BASE_URL}/api/v1/missions/{mission_id}" 
            async with httpx.AsyncClient() as client:
                status_response = await client.get(mission_status_url)
                
                if status_response.status_code == 200:
                    mission_data = status_response.json()
                    mission_status = mission_data.get('status', '').upper()
                    log.info(f"Mission {mission_id} status: {mission_status}")
                    
                    if mission_status == "COMPLETED":
                        mission_completed = True
                        break # Exit loop on completion
                    elif mission_status in ["FAILED", "ABORTED"]:
                        pytest.fail(f"Mission ended with failure status: {mission_status} - Reason: {mission_data.get('failure_reason')}")
                
                elif status_response.status_code == 404:
                    log.debug(f"Mission {mission_id} not found yet...")
                else:
                    log.warning(f"Error checking mission status: {status_response.status_code} - {status_response.text}")
        
        except httpx.RequestError as e:
            log.warning(f"Could not connect to check mission status: {e}")
        except Exception as e:
             log.error(f"Error parsing mission status response: {e}")

        # Fallback: If no mission endpoint, check for drone state via /api/v1/drones/{drone_id}
        # try:
        #     drone_status_url = f"{API_BASE_URL}/api/v1/drones/{drone_id}"
        #     async with httpx.AsyncClient() as client:
        #         drone_res = await client.get(drone_status_url)
        #         if drone_res.status_code == 200:
        #             drone_data = drone_res.json()
        #             drone_state = drone_data.get('state', {}).get('state_name', '').upper()
        #             log.info(f"Drone {drone_id} state: {drone_state}")
        #             # Check if landed after mission
        #             if drone_state == "MISSION_COMPLETED":
        #                   mission_completed = True
        #                   break
        #             if drone_state in ["MISSION_FAILED", "EMERGENCY_LANDING"]:
        #                   pytest.fail(f"Drone ended in failure state: {drone_state}")
        # except httpx.RequestError as e:
        #      log.warning(f"Could not check drone status: {e}")


        await asyncio.sleep(poll_interval)

    # 3. Final Assertions
    # Note: This assertion might fail if the /api/v1/missions/{id} endpoint doesn't exist yet
    assert mission_completed, f"Mission {mission_id} did not complete within {max_wait_time} seconds. (Check API endpoint: {mission_status_url})"
    # Optionally assert final ACK status if checked
    # assert ack_status == "completed", f"Expected final ACK status 'completed', got {ack_status}"

    log.info(f"Integration Test Passed: Mission {mission_id} completed.")

# Add more integration tests for RTL, GOTO, Failsafes (requires fault injection)
