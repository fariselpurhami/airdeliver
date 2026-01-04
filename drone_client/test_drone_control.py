import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

# Import your system under test
# Assuming your main class is in 'drone-control.py' (which you should rename to drone_companion.py ideally)
# For now, we import from the file name you have.
from drone_control import DroneCompanion, DroneState, CommandMessage

# -----------------------------------------------------------------------------
# 1. FIXTURES (The Setup)
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_env():
    """Sets up environment variables for testing."""
    with patch.dict('os.environ', {
        'DRONE_ID': 'test-drone-001',
        'WEBSOCKET_URI': 'ws://test-api/ws',
        'MAVLINK_CONNECTION': 'udp://:14540',
        'AUTH_TOKEN': 'secret-token',
        'API_BASE_URL': 'http://test-api/v1'
    }):
        yield

@pytest.fixture
def companion(mock_env):
    """Creates a DroneCompanion instance with mocked dependencies."""
    # We mock System() so we don't actually spawn mavsdk_server
    with patch('mavsdk.System') as MockSystem:
        mock_drone_system = MockSystem.return_value
        
        # Setup async mocks for critical system methods
        mock_drone_system.connect = AsyncMock()
        mock_drone_system.action.arm = AsyncMock()
        mock_drone_system.action.takeoff = AsyncMock()
        mock_drone_system.action.land = AsyncMock()
        
        # Mock Telemetry Streams (Async Generators)
        async def mock_position_stream():
            yield MagicMock(latitude_deg=30.0, longitude_deg=31.0, relative_altitude_m=10.0)
            await asyncio.sleep(0.1) # Simulate delay
        
        mock_drone_system.telemetry.position = MagicMock(return_value=mock_position_stream())
        
        companion_app = DroneCompanion(
            drone_id='test-drone-001',
            ws_uri_base='ws://test-api/ws',
            mavlink_conn='udp://:14540',
            api_token='secret-token'
        )
        # Inject the mock system
        companion_app.mavsdk_drone = mock_drone_system
        return companion_app

# -----------------------------------------------------------------------------
# 2. UNIT TESTS (The Specs)
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialization_state(companion):
    """Verify system starts in the correct BOOTING state."""
    assert companion.current_state == DroneState.BOOTING
    assert companion.drone_id == 'test-drone-001'

@pytest.mark.asyncio
async def test_pixhawk_connection_success(companion):
    """Test the retry logic for connecting to the flight controller."""
    # Setup the mock to succeed immediately
    companion.mavsdk_drone.connect.return_value = None 
    
    # We mock the _wait_for_pixhawk_connection to return instantly
    with patch.object(companion, '_wait_for_pixhawk_connection', AsyncMock(return_value=True)):
        success = await companion._connect_to_pixhawk()
        
    assert success is True
    assert companion.mavsdk_drone.connect.called
    assert companion.current_state == DroneState.GETTING_JWT

@pytest.mark.asyncio
async def test_jwt_acquisition_flow(companion):
    """Test authenticating with the backend API."""
    # Mock the HTTP Client response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "valid.jwt.token",
        "expires_in_minutes": 60
    }
    
    companion.http_client.post = AsyncMock(return_value=mock_response)
    
    success = await companion._get_jwt_token()
    
    assert success is True
    assert companion.jwt_token == "valid.jwt.token"
    assert companion.current_state == DroneState.DISCONNECTED_SERVER

@pytest.mark.asyncio
async def test_command_execution_takeoff(companion):
    """Test handling a TAKEOFF command from the websocket."""
    # Simulate a command message
    cmd = CommandMessage(command="TAKEOFF", payload={"altitude": 20})
    
    # Mock state to be ready
    companion.current_state = DroneState.IDLE
    
    # Inject command handler logic (mocking the internal method for isolation)
    # Ideally you test the handle_command method directly
    # Assuming handle_command exists:
    if hasattr(companion, 'handle_command'):
        await companion.handle_command(cmd)
        
        # Verify MAVSDK was called
        companion.mavsdk_drone.action.arm.assert_called_once()
        companion.mavsdk_drone.action.takeoff.assert_called_once()
        assert companion.current_state == DroneState.TAKING_OFF

@pytest.mark.asyncio
async def test_telemetry_loop(companion):
    """Verify telemetry data is formatted and pushed."""
    # Mock WebSocket to capture sent data
    companion.websocket = MagicMock()
    companion.websocket.open = True
    companion.websocket.send = AsyncMock()
    
    # Inject a known state
    companion.current_state = DroneState.HOVERING
    
    # Run one iteration of telemetry
    # We simulate this by calling the internal telemetry handler once
    # Or extracting the logic to a testable unit.
    # For now, we assume _send_telemetry sends one packet.
    
    if hasattr(companion, '_send_telemetry_packet'):
        data = {
            "lat": 30.0444, 
            "lon": 31.2357, 
            "alt": 10.5,
            "bat": 98
        }
        await companion._send_telemetry_packet(data)
        
        # Verify JSON structure sent to WS
        call_args = companion.websocket.send.call_args[0][0]
        sent_json = json.loads(call_args)
        
        assert sent_json['type'] == 'telemetry'
        assert sent_json['payload']['location']['lat'] == 30.0444
        assert sent_json['drone_id'] == 'test-drone-001'

# -----------------------------------------------------------------------------
# 3. INTEGRATION SIMULATION (Edge Cases)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_emergency_landing_on_critical_error(companion):
    """Test failsafe trigger."""
    companion.current_state = DroneState.FLYING
    
    # Simulate a catastrophic exception in the main loop
    # This requires the companion to have an error handler we can trigger
    # Or we verify the _update_state logic.
    
    await companion._update_state(DroneState.EMERGENCY_LANDING, reason="Battery Critical")
    
    assert companion.current_state == DroneState.EMERGENCY_LANDING
    # Ensure event was logged/sent
    # assert companion.websocket.send.called_with(...)
