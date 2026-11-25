"""Synthetic private values must be absent from raw records, not just JSON formatting."""
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request
from starlette.websockets import WebSocketDisconnect, WebSocketState
from app.api.v1.endpoints import orders, webhooks, ai_ordering
from tests.test_webhook_security import request_for, signed_header, settings as stripe_settings

PRIVATE = "PRIVATE_RAW_RECORD_MARKER"


def assert_clean(caplog):
    assert caplog.records
    assert PRIVATE not in json.dumps([vars(r) for r in caplog.records], default=str)
    assert all(r.exc_info is None and r.stack_info is None for r in caplog.records)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [SQLAlchemyError, RuntimeError])
async def test_orders_database_and_unexpected_errors_have_no_raw_payload(caplog, failure):
    caplog.set_level(logging.INFO)
    with pytest.raises(HTTPException) as caught:
        await orders.read_my_orders(response=Response(), session=SimpleNamespace(execute=AsyncMock(side_effect=failure(PRIVATE))), current_user=SimpleNamespace(id=7), page=1, limit=10)
    assert caught.value.status_code == 500
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_stripe_callback_internal_error_is_retryable_without_private_logs(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(webhooks, "_delegate_payment_success", AsyncMock(side_effect=RuntimeError(PRIVATE)))
    body=json.dumps({"type":"payment_intent.succeeded","data":{"object":{}}}).encode()
    with pytest.raises(HTTPException) as caught:
        await webhooks.stripe_webhook(request_for(body),signed_header(body),stripe_settings(),AsyncMock(),AsyncMock(),AsyncMock())
    assert caught.value.status_code == 503
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_paypal_callback_internal_error_has_no_traceback_payload(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    fake=SimpleNamespace(verify_webhook_signature=AsyncMock(side_effect=RuntimeError(PRIVATE)))
    monkeypatch.setattr(webhooks,"PayPalGateway",lambda *args:fake)
    with pytest.raises(HTTPException) as caught:
        await webhooks.paypal_webhook(request_for(b'{}'),SimpleNamespace(PAYPAL_WEBHOOK_ID="synthetic"),AsyncMock(),AsyncMock(),AsyncMock())
    assert caught.value.status_code == 503
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_rate_limit_cache_outage_keeps_existing_policy_without_payload(caplog):
    caplog.set_level(logging.INFO)
    assert await ai_ordering.check_rate_limit(7,SimpleNamespace(incr=AsyncMock(side_effect=RuntimeError(PRIVATE)))) is True
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_websocket_auth_error_never_logs_ticket_or_exception(monkeypatch,caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(ai_ordering.deps,"get_current_active_user_ws_ticket",AsyncMock(side_effect=RuntimeError(PRIVATE)))
    ws=SimpleNamespace(client_state=WebSocketState.CONNECTED,close=AsyncMock())
    await ai_ordering.handle_chat_websocket(ws,PRIVATE,AsyncMock(),AsyncMock(),AsyncMock())
    ws.close.assert_awaited_once_with(code=1008)
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_rejected_voice_ticket_not_logged(caplog):
    caplog.set_level(logging.INFO)
    ws=SimpleNamespace(close=AsyncMock())
    await ai_ordering.handle_voice_stream(ws,PRIVATE,AsyncMock(),object(),object(),AsyncMock(),SimpleNamespace(get=AsyncMock(return_value=None)))
    ws.close.assert_awaited_once_with(code=1008)
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_global_handler_does_not_log_arbitrary_path_or_exception(caplog):
    from app.main import register_exception_handlers
    caplog.set_level(logging.INFO)
    app=FastAPI();register_exception_handlers(app)
    request=Request({"type":"http","method":"GET","path":"/product/"+PRIVATE,"headers":[]})
    try:
        raise RuntimeError(PRIVATE)
    except RuntimeError as exc:
        response=await app.exception_handlers[Exception](request,exc)
    assert response.status_code==500
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_client_selected_socket_command_type_is_not_a_log_field(monkeypatch,caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(ai_ordering.deps,"get_current_active_user_ws_ticket",AsyncMock(return_value=SimpleNamespace(id=7)))
    monkeypatch.setattr(ai_ordering.deps,"get_websocket_manager",lambda:SimpleNamespace(connect=AsyncMock(),disconnect=AsyncMock()))
    cache=SimpleNamespace(incr=AsyncMock(return_value=2))
    ws=SimpleNamespace(client_state=WebSocketState.CONNECTED,accept=AsyncMock(),close=AsyncMock(),send_json=AsyncMock(),receive_text=AsyncMock(side_effect=[json.dumps({"type":PRIVATE}),WebSocketDisconnect(code=1000)]))
    await ai_ordering.handle_chat_websocket(ws,"synthetic",AsyncMock(),AsyncMock(),cache)
    assert ws.send_json.await_args.args[0]["code"]=="UNSUPPORTED_CHANNEL"
    assert_clean(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["setup", "listener", "receive", "cancel"])
async def test_socket_failure_phases_and_cancellation_keep_private_data_out(monkeypatch,caplog,phase):
    import asyncio
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(ai_ordering.deps,"get_current_active_user_ws_ticket",AsyncMock(return_value=SimpleNamespace(id=7)))
    manager=SimpleNamespace(connect=AsyncMock(),disconnect=AsyncMock())
    monkeypatch.setattr(ai_ordering.deps,"get_websocket_manager",lambda:manager)
    async def listen():
        raise RuntimeError(PRIVATE)
        yield
    pubsub=SimpleNamespace(listen=listen,close=AsyncMock())
    cache=SimpleNamespace(subscribe=AsyncMock(side_effect=RuntimeError(PRIVATE) if phase=="setup" else None,return_value=pubsub))
    async def receive():
        await asyncio.sleep(0)
        if phase=="cancel": raise asyncio.CancelledError()
        if phase=="receive": raise RuntimeError(PRIVATE)
        raise WebSocketDisconnect(code=1000)
    ws=SimpleNamespace(client_state=WebSocketState.CONNECTED,accept=AsyncMock(),close=AsyncMock(),receive_text=receive)
    if phase=="cancel":
        with pytest.raises(asyncio.CancelledError):
            await ai_ordering.handle_chat_websocket(ws,"synthetic",AsyncMock(),AsyncMock(),cache)
    else:
        await ai_ordering.handle_chat_websocket(ws,"synthetic",AsyncMock(),AsyncMock(),cache)
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_redis_bridge_retries_then_propagates_without_traceback(monkeypatch,caplog):
    from app import main
    from redis.exceptions import ConnectionError
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(main.asyncio,"sleep",AsyncMock())
    class Process:
        async def __aenter__(self): pass
        async def __aexit__(self,kind,*args): assert kind is ConnectionError
    cache=SimpleNamespace(publish_required=AsyncMock(side_effect=ConnectionError(PRIVATE)))
    message=SimpleNamespace(body=b'{"user_id":7}',process=lambda **kwargs:Process())
    with pytest.raises(ConnectionError):
        await main.relay_response_message(message,AsyncMock(),cache)
    assert cache.publish_required.await_count==3
    assert_clean(caplog)


@pytest.mark.asyncio
async def test_voice_orchestrator_failure_keeps_cleanup_and_no_traceback(monkeypatch,caplog):
    caplog.set_level(logging.INFO)
    orchestrator=SimpleNamespace(process_voice_session=AsyncMock(side_effect=RuntimeError(PRIVATE)))
    monkeypatch.setattr(ai_ordering,"AIVoiceOrchestrator",lambda **kwargs:orchestrator)
    cache=SimpleNamespace(get=AsyncMock(side_effect=["7",None]),set=AsyncMock(),delete=AsyncMock())
    ws=SimpleNamespace(close=AsyncMock())
    await ai_ordering.handle_voice_stream(ws,"synthetic",AsyncMock(),object(),object(),AsyncMock(),cache)
    ws.close.assert_awaited_once_with(code=1011)
    assert cache.delete.await_count==2
    assert_clean(caplog)
