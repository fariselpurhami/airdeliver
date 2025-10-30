# apps/api/tests/websockets/test_tracking_ws.py

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from unittest.mock import patch, AsyncMock, MagicMock
import json
from datetime import datetime, timezone
from app.main import app
from app.websockets.tracking_ws import TelemetryMessage, TelemetryPayload

pytestmark = pytest.mark.asyncio

@pytest.fixture
def test_client():

    return TestClient(app)

async def test_websocket_valid_handshake():
    client = TestClient(app)
    drone_id = "TEST-001"
    
    with patch("app.websockets.tracking_ws.verify_token", new_callable=AsyncMock, return_value=True):
        with client.websocket_connect(f"/ws/drones/{drone_id}") as websocket:
        
            handshake = {"type": "connect", "drone_id": drone_id, "token": "valid_token"}
            websocket.send_json(handshake)
    
            response = websocket.receive_json()
            assert response == {"status": "connected", "drone_id": drone_id}

async def test_websocket_invalid_token():
    client = TestClient(app)
    drone_id = "TEST-002"
    with patch("app.websockets.tracking_ws.verify_token", new_callable=AsyncMock, return_value=False):
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws/drones/{drone_id}") as websocket:
                handshake = {"type": "connect", "drone_id": drone_id, "token": "invalid_token"}
                websocket.send_json(handshake)
                websocket.receive_json() 
        assert excinfo.value.code == 1008 

async def test_websocket_handle_telemetry():
    client = TestClient(app)
    drone_id = "TEST-003"
    
    with patch("app.websockets.tracking_ws.verify_token", new_callable=AsyncMock, return_value=True), \
         patch("app.websockets.tracking_ws.BackgroundTasks.add_task") as mock_add_task, \
         patch("app.websockets.tracking_ws.update_last_seen", new_callable=AsyncMock) as mock_update_last_seen:
        with client.websocket_connect(f"/ws/drones/{drone_id}") as websocket:
            
            handshake = {"type": "connect", "drone_id": drone_id, "token": "valid_token"}
            websocket.send_json(handshake)
            websocket.receive_json() 

            telemetry_payload = {
                "lat": 10.0, "lon": 20.0, "alt_m": 50.0, "ground_speed_m_s": 5.0, "battery_pct": 90
            }
            telemetry_msg = {
                "type": "telemetry", "drone_id": drone_id, "payload": telemetry_payload
            
            }
            websocket.send_json(telemetry_msg)

            await asyncio.sleep(0.1) 
            mock_update_last_seen.assert_called_once_with(drone_id)
            mock_add_task.assert_called_once()
        
            args, kwargs = mock_add_task.call_args
            assert args[0].__name__ == "persist_data" 
            assert args[1] == f"/drones/{drone_id}/telemetry"
        
            persisted_payload = args[2]
            assert persisted_payload["drone_id"] == drone_id
            assert persisted_payload["lat"] == telemetry_payload["lat"]
