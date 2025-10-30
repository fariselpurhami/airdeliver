# tests/integration/test_drone_simulation.py 

import subprocess
import time
import httpx
import json
import uuid
import pytest
import asyncio
import logging 
from datetime import datetime, timezone

log = logging.getLogger("IntegrationTest")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not log.hasHandlers():
    log.addHandler(handler)

DOCKER_COMPOSE_FILES = "-f docker-compose.yml -f docker-compose.drone.yml"
API_BASE_URL = "http://localhost:8000" 
WS_INTERNAL_BASE_URL = f"{API_BASE_URL}/ws/internal" 

@pytest.fixture(scope="module", autouse=True)
def run_simulation_stack():
    log.info("Setting up simulation stack...")
    try:
        
        subprocess.run(f"docker compose {DOCKER_COMPOSE_FILES} down -v --remove-orphans", shell=True, check=True, capture_output=True, text=True)
        
        up_result = subprocess.run(f"docker compose {DOCKER_COMPOSE_FILES} up --build -d", shell=True, check=True, capture_output=True, text=True)
        log.info(up_result.stdout)
        log.error(up_result.stderr)
        
        log.info("Waiting for services to stabilize...")
    
        wait_for_service(f"{API_BASE_URL}/ws/health", expected_status="ok", timeout=120)
    
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

    mission_payload_data = {
        "action": "start_mission",
        "mission": {
            "mission_id": mission_id,
            "waypoints": [
        
                {"lat": 34.0530, "lon": -118.2440, "alt_m": 10.0},
                {"lat": 34.0535, "lon": -118.2445, "alt_m": 12.0},
                {"lat": 34.0530, "lon": -118.2450, "alt_m": 10.0}, 
            ]
        },
        "requires_ack": True
    }
    command_message = {
        "type": "command", "command_id": command_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": mission_payload_data
    }


    log.info(f"Sending mission command {command_id} to {drone_id}...")
    send_url = f"{WS_INTERNAL_BASE_URL}/send_command/{drone_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(send_url, json=command_message)
            response.raise_for_status() 
            log.info(f"Send command response: {response.status_code}, {response.text}")
            assert response.status_code == 202
        
            assert response.json()["status"] in ["command_accepted", "pending_send"] 
        except httpx.HTTPStatusError as e:
            pytest.fail(f"Failed to send command: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            pytest.fail(f"Failed to connect to send command endpoint: {e}")


    max_wait_time = 180 
    poll_interval = 5   
    start_poll_time = time.monotonic()
    mission_completed = False
    ack_status = None

    log.info(f"Polling for ACK and mission completion (max {max_wait_time}s)...")
    while time.monotonic() - start_poll_time < max_wait_time:
        
        try:
        
            mission_status_url = f"{API_BASE_URL}/api/v1/missions/{mission_id}" 
            async with httpx.AsyncClient() as client:
                status_response = await client.get(mission_status_url)
                
                if status_response.status_code == 200:
                    mission_data = status_response.json()
                    mission_status = mission_data.get('status', '').upper()
                    log.info(f"Mission {mission_id} status: {mission_status}")
                    
                    if mission_status == "COMPLETED":
                        mission_completed = True
                        break 
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

        await asyncio.sleep(poll_interval)

    assert mission_completed, f"Mission {mission_id} did not complete within {max_wait_time} seconds. (Check API endpoint: {mission_status_url})"

    log.info(f"Integration Test Passed: Mission {mission_id} completed.")
