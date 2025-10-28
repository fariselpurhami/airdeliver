# file: apps/api/tests/websockets/test_tracking_ws.py
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from unittest.mock import patch, AsyncMock, MagicMock
import json
from datetime import datetime, timezone

# Import the router or app where WS is mounted (adjust import based on your structure)
# Assuming main app includes the router
from app.main import app
# Import schemas used
from app.websockets.tracking_ws import TelemetryMessage, TelemetryPayload

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

# --- Fixtures ---
@pytest.fixture
def test_client():
    # Use TestClient for HTTP requests like send_command
    return TestClient(app)

# --- Test Cases ---

# Test WebSocket Connection and Handshake
async def test_websocket_valid_handshake():
    client = TestClient(app)
    drone_id = "TEST-001"
    # Mock verify_token to return True
    with patch("app.websockets.tracking_ws.verify_token", new_callable=AsyncMock, return_value=True):
        with client.websocket_connect(f"/ws/drones/{drone_id}") as websocket:
            # Send valid handshake
            handshake = {"type": "connect", "drone_id": drone_id, "token": "valid_token"}
            websocket.send_json(handshake)
            # Receive confirmation
            response = websocket.receive_json()
            assert response == {"status": "connected", "drone_id": drone_id}
            # Check if drone is registered (mock register_drone or check internal state if possible)

async def test_websocket_invalid_token():
    client = TestClient(app)
    drone_id = "TEST-002"
    with patch("app.websockets.tracking_ws.verify_token", new_callable=AsyncMock, return_value=False):
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws/drones/{drone_id}") as websocket:
                handshake = {"type": "connect", "drone_id": drone_id, "token": "invalid_token"}
                websocket.send_json(handshake)
                websocket.receive_json() # Should disconnect here
        assert excinfo.value.code == 1008 # Policy violation

# Test Telemetry Handling
async def test_websocket_handle_telemetry():
    client = TestClient(app)
    drone_id = "TEST-003"
    # Mock verify_token and background task runner
    with patch("app.websockets.tracking_ws.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("app.websockets.tracking_ws.BackgroundTasks.add_task") as mock_add_task, \
         patch("app.websockets.tracking_ws.update_last_seen", new_callable=AsyncMock) as mock_update_last_seen:
        with client.websocket_connect(f"/ws/drones/{drone_id}") as websocket:
            # Connect
            handshake = {"type": "connect", "drone_id": drone_id, "token": "valid_token"}
            websocket.send_json(handshake)
            websocket.receive_json() # Consume connect confirmation

            # Send valid telemetry
            telemetry_payload = {
                "lat": 10.0, "lon": 20.0, "alt_m": 50.0, "ground_speed_m_s": 5.0, "battery_pct": 90
            }
            telemetry_msg = {
                "type": "telemetry", "drone_id": drone_id, "payload": telemetry_payload
                # Timestamp added automatically by model or server
            }
            websocket.send_json(telemetry_msg)

            # Assertions
            await asyncio.sleep(0.1) # Allow time for processing
            mock_update_last_seen.assert_called_once_with(drone_id)
            mock_add_task.assert_called_once()
            # Check the arguments passed to persist_data task
            args, kwargs = mock_add_task.call_args
            assert args[0].__name__ == "persist_data" # Check task function name
            assert args[1] == f"/drones/{drone_id}/telemetry" # Check endpoint path
            # Check persisted payload (approximate match, ignore timestamp details if complex)
            persisted_payload = args[2]
            assert persisted_payload["drone_id"] == drone_id
            assert persisted_payload["lat"] == telemetry_payload["lat"]
            # ... check other fields ...

# Add more unit tests for handle_event, handle_ack, send_command logic, etc.
