# tests/integration/test_global_architecture.py

import pytest
import asyncio
import json
import uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlmodel import Session, select

from app.main import app as fastapi_app
from app.db.session import get_session
from app.services.rabbitmq_service import rabbitmq_service
from app.services import telemetry_consumer, event_consumer
from app import models
from app.core.config import settings

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module", autouse=True)
async def setup_rabbitmq_consumers():
    await rabbitmq_service.connect()
    
    tasks = [
        asyncio.create_task(telemetry_consumer.consume_telemetry(rabbitmq_service.connection_pool)),
        asyncio.create_task(event_consumer.consume_events(rabbitmq_service.connection_pool))
    ]
    
    await asyncio.sleep(2)
    yield
    
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await rabbitmq_service.disconnect()

@pytest.fixture(scope="module")
async def async_client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client

@pytest.fixture(scope="module")
async def superuser_token_headers(async_client: AsyncClient) -> dict[str, str]:
    return {"Authorization": "Bearer FAKE_SUPERUSER_TOKEN"}

@pytest.fixture
async def test_drone(session: Session) -> models.Drone:
    drone_id_str = f"INTEG-TEST-{uuid.uuid4().hex[:6]}"
    drone = models.Drone(
        drone_id_str=drone_id_str,
        model="TestVTOL",
        status=models.DroneStatus.IDLE,
        home_base_lat=34.0,
        home_base_lon=-118.0
    )
    session.add(drone)
    await session.commit()
    await session.refresh(drone)
    return drone

@pytest.mark.asyncio
async def test_e2e_telemetry_and_event_flow(
    async_client: AsyncClient,
    session: Session,
    test_drone: models.Drone,
    setup_rabbitmq_consumers
):
    drone_id = test_drone.drone_id_str
    mission_id = f"m-integ-{uuid.uuid4().hex[:6]}"

    telemetry_payload = {
        "drone_id": drone_id,
        "timestamp": datetime.now().isoformat(),
        "mission_id_str": mission_id,
        "lat": 34.0001,
        "lon": -118.0001,
        "alt_m": 150.0,
        "ground_speed_m_s": 41.0,
        "battery_pct": 88,
        "flight_mode": "MISSION"
    }
    telemetry_message = {"type": "telemetry", "payload": telemetry_payload}
    
    await rabbitmq_service.publish_message(
        settings.EXCHANGE_TELEMETRY,
        f"drone.{drone_id}",
        json.dumps(telemetry_message).encode()
    )

    await asyncio.sleep(1.0) 
    
    await session.refresh(test_drone)
    assert test_drone.current_lat == 34.0001
    assert test_drone.current_battery_pct == 88
    assert test_drone.status == models.DroneStatus.IN_MISSION

    event_payload = {
        "drone_id": drone_id,
        "timestamp": datetime.now().isoformat(),
        "event_type": models.EventType.LANDED.value,
        "mission_id_str": mission_id,
        "details": {"reason": "Mission Complete"}
    }
    event_message = {"type": "event", "payload": event_payload}

    mission = models.Mission(
        mission_id_str=mission_id,
        status=models.MissionStatus.IN_PROGRESS,
        assigned_drone_id=test_drone.id
    )
    session.add(mission)
    await session.commit()

    await rabbitmq_service.publish_message(
        settings.EXCHANGE_EVENTS,
        f"drone.{drone_id}",
        json.dumps(event_message).encode()
    )

    await asyncio.sleep(1.0)
    
    await session.refresh(test_drone)
    await session.refresh(mission)
    
    assert test_drone.status == models.DroneStatus.IDLE
    assert mission.status == models.MissionStatus.COMPLETED

@pytest.mark.asyncio
async def test_e2e_command_flow(
    async_client: AsyncClient,
    session: Session,
    test_drone: models.Drone,
    superuser_token_headers: dict[str, str],
    setup_rabbitmq_consumers
):
    drone_id = test_drone.drone_id_str
    mission_id = f"m-cmd-{uuid.uuid4().hex[:6]}"
    
    mission_payload = {
        "mission_id": mission_id,
        "waypoints": [{"lat": 34.1, "lon": -118.1, "alt_m": 150.0}]
    }

    queue = None
    channel = None
    try:
        async with rabbitmq_service.channel_pool.acquire() as channel:
            queue_name = f"{settings.QUEUE_COMMANDS_PREFIX}.{drone_id}"
            routing_key = f"drone.{drone_id}"
            
            queue = await channel.declare_queue(
                queue_name, durable=True, exclusive=False, auto_delete=False
            )
            await queue.bind(settings.EXCHANGE_COMMANDS, routing_key=routing_key)
            await queue.purge()

            response = await async_client.post(
                f"/api/v1/commands/{drone_id}/start_mission",
                json=mission_payload,
                headers=superuser_token_headers
            )
            
            assert response.status_code == 202

            try:
                incoming_message = await asyncio.wait_for(queue.get(timeout=2.0), timeout=2.0)
                assert incoming_message is not None
                
                async with incoming_message.process():
                    data = json.loads(incoming_message.body.decode())
                    assert data["command"] == "start_mission"
                    assert data["payload"]["mission_id"] == mission_id
                    assert data["payload"]["waypoints"][0]["lat"] == 34.1
                    
            except asyncio.TimeoutError:
                pytest.fail("Command message was not received in RabbitMQ queue within timeout.")

    finally:
        if queue and channel:
            await queue.unbind(settings.EXCHANGE_COMMANDS)
