"""Exercise API response wiring with the real broker-service interface."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from app import main
from app.core.config import get_core_settings
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import NoOpCacheClient


@pytest.mark.asyncio
async def test_actual_broker_service_binds_and_relays_response(monkeypatch):
    service = RabbitMQService(get_core_settings())
    queue = AsyncMock()
    exchange = object()
    service._topology = SimpleNamespace(
        connection=SimpleNamespace(is_closed=False),
        channel=SimpleNamespace(is_closed=False, declare_queue=AsyncMock(return_value=queue)),
        exchange=exchange,
    )
    app = FastAPI()
    app.state.resources = main.ApplicationResources(cache=NoOpCacheClient(), rabbitmq=service)
    from app.api.deps import WebSocketManager
    manager = WebSocketManager()
    socket = MagicMock()
    socket.send_text = AsyncMock()
    await manager.connect(99, socket)
    monkeypatch.setattr(main, "get_websocket_manager", lambda: manager)
    await main.start_response_consumer(app)
    queue.bind.assert_awaited_once_with(exchange, routing_key=main.RESPONSE_ROUTING_KEY)
    callback = queue.consume.await_args.args[0]
    class Process:
        async def __aenter__(self):
            pass
        async def __aexit__(self, *args):
            pass
    message = SimpleNamespace(body=json.dumps({"user_id": 99, "type": "ORDER_CONFIRMED"}).encode(), process=lambda **kwargs: Process())
    await callback(message)
    socket.send_text.assert_awaited_once()
    assert json.loads(socket.send_text.await_args.args[0])["type"] == "ORDER_CONFIRMED"
    socket.send_text.reset_mock()
    message.body = json.dumps({"user_id": "100", "type": "ORDER_CONFIRMED"}).encode()
    await callback(message)
    socket.send_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_api_startup_waits_for_consumer_and_closes_resources_if_binding_fails(monkeypatch):
    cache, broker = AsyncMock(), AsyncMock()
    monkeypatch.setattr(main, "initialize_cache_client", AsyncMock(return_value=cache))
    monkeypatch.setattr(main, "get_rabbitmq_service", AsyncMock(return_value=broker))
    monkeypatch.setattr(main, "start_response_consumer", AsyncMock(side_effect=RuntimeError("bind failed")))
    with pytest.raises(RuntimeError, match="bind failed"):
        await main.startup_resources(FastAPI(), get_core_settings())
    broker.close.assert_awaited_once()
    cache.disconnect.assert_awaited_once()


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, None, {}, " ", "abc", "0", "-1", "1e2"])
def test_response_identity_rejects_ambiguous_values(value):
    with pytest.raises(main.InvalidMessageError):
        main.extract_user_id({"user_id": value})


def test_response_identity_accepts_positive_integer_producer_contract():
    assert main.extract_user_id({"user_id": 99}) == 99
    assert main.extract_user_id({"user_id": "99"}) == 99


@pytest.mark.asyncio
async def test_broker_response_reaches_socket_in_another_api_process():
    from app.api.deps import WebSocketManager
    local_manager, remote_manager = WebSocketManager(), WebSocketManager()
    socket = MagicMock()
    socket.send_text = AsyncMock()
    await remote_manager.connect(99, socket)
    class SharedRedis:
        async def publish(self, channel, body):
            assert channel == "airdeliver:response:99"
            await remote_manager.send_to_user(99, body)
            return 1
    class Process:
        async def __aenter__(self):
            pass
        async def __aexit__(self, *args):
            pass
    message = SimpleNamespace(body=b'{"user_id":99,"type":"ORDER_CONFIRMED"}', process=lambda **kwargs: Process())
    await main.relay_response_message(message, local_manager, cache=SharedRedis())
    socket.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_bridge_failure_is_not_silently_acknowledged():
    class Process:
        async def __aenter__(self):
            pass
        async def __aexit__(self, exc_type, *args):
            assert exc_type is ValueError
    cache = AsyncMock()
    cache.publish.side_effect = ValueError("invalid backend state")
    message = SimpleNamespace(body=b'{"user_id":99}', process=lambda **kwargs: Process())
    with pytest.raises(ValueError, match="invalid backend"):
        await main.relay_response_message(message, AsyncMock(), cache=cache)
