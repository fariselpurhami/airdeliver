"""Runtime service-level log failures with synthetic data and controlled adapters."""
import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from tests.test_raw_route_log_privacy import PRIVATE, assert_clean


@pytest.mark.asyncio
async def test_payment_gateway_fault_preserves_failure_without_raw_exception(caplog):
    from tests.test_payment_orchestrator import FakeGateway, make_request
    from app.services.payment_orchestrator import GatewayProvider, PaymentOrchestrator, PaymentStatus
    caplog.set_level(logging.INFO)
    gateway=FakeGateway(GatewayProvider.STRIPE,exc=RuntimeError(PRIVATE))
    response=await PaymentOrchestrator([gateway]).process_payment(make_request(),"synthetic")
    assert response.status==PaymentStatus.FAILURE
    assert gateway.calls==1
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_paypal_cache_failure_keeps_existing_fetch_and_token_return(monkeypatch,caplog):
    import httpx
    from tests.test_paypal_capture_security import gateway, order_body
    caplog.set_level(logging.INFO)
    gw,client,calls=gateway(order_body())
    gw._cache.get=AsyncMock(side_effect=RuntimeError(PRIVATE))
    gw._cache.set=AsyncMock(side_effect=RuntimeError(PRIVATE))
    def transport(request):
        calls.append(request)
        return httpx.Response(200,json={"access_token":"synthetic-token","expires_in":300})
    client._transport=httpx.MockTransport(transport)
    async with client:
        token=await gw._get_access_token()
    assert token=="synthetic-token"
    assert len(calls)==1
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_nlu_cache_key_failure_does_not_log_key_or_exception(caplog):
    from tests.test_nlu_behavior_contracts import service
    caplog.set_level(logging.INFO)
    svc=service();svc.cache=SimpleNamespace(delete=AsyncMock(side_effect=RuntimeError(PRIVATE)))
    await svc._safe_delete_cache_key(PRIVATE)
    assert_clean(caplog)


def test_retained_structured_logging_entrypoint_uses_same_private_boundary(caplog):
    from app.services.ai_nlu_service import StructuredLog
    caplog.set_level(logging.INFO)
    try:
        raise RuntimeError(PRIVATE)
    except RuntimeError:
        StructuredLog._legacy_emit(logging.ERROR,"synthetic_failure",exc_info=True,query=PRIVATE,error=PRIVATE,user_id=7)
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_socket_send_failure_still_evicts_broken_connection_without_payload(caplog):
    from app.api.deps import WebSocketManager
    caplog.set_level(logging.INFO)
    manager=WebSocketManager()
    socket=MagicMock();socket.send_text=AsyncMock(side_effect=ValueError(PRIVATE))
    await manager.connect(7,socket)
    await manager.send_to_user(7,PRIVATE)
    assert not manager._active_connections.get(7)
    assert_clean(caplog)
