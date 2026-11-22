# apps/api/tests/test_ai_voice_service.py
"""Tests for ai_voice_service: config guards + tool executor logic."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.ai_voice_service import CartAction, VoiceConfig, VoiceToolExecutor


# --- VoiceConfig ---

def test_ws_url_requires_agent_id(monkeypatch):
    monkeypatch.setattr(VoiceConfig, "ELEVENLABS_AGENT_ID", None)
    with pytest.raises(ValueError, match="ELEVENLABS_AGENT_ID"):
        VoiceConfig.get_ws_url()


def test_ws_url_format(monkeypatch):
    monkeypatch.setattr(VoiceConfig, "ELEVENLABS_AGENT_ID", "agent-123")
    url = VoiceConfig.get_ws_url()
    assert url == "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=agent-123"


def test_auth_headers_require_key(monkeypatch):
    monkeypatch.setattr(VoiceConfig, "ELEVENLABS_API_KEY", None)
    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        VoiceConfig.get_auth_headers()


def test_auth_headers_use_xi_api_key(monkeypatch):
    monkeypatch.setattr(VoiceConfig, "ELEVENLABS_API_KEY", "sk_test")
    assert VoiceConfig.get_auth_headers() == {"xi-api-key": "sk_test"}


# --- VoiceToolExecutor ---

class FakeWS:
    def __init__(self, fail=False):
        self.sent = []
        self._fail = fail

    async def send_text(self, text):
        if self._fail:
            raise ConnectionError("client gone")
        self.sent.append(json.loads(text))


def make_executor(products=None, web_intel="intel"):
    commerce = SimpleNamespace(
        perform_hybrid_search_pure=AsyncMock(return_value=products or [])
    )
    llm = SimpleNamespace(_perform_web_search=AsyncMock(return_value=web_intel))
    rabbit = SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=True)))
    executor = VoiceToolExecutor(
        commerce_engine=commerce,
        llm_service=llm,
        rabbitmq=rabbit,
        cache=SimpleNamespace(),
        db_session=SimpleNamespace(),
    )
    return executor, commerce, llm, rabbit


@pytest.mark.asyncio
async def test_search_no_matches_returns_status():
    executor, *_ = make_executor(products=[])
    out = json.loads(await executor.search_global_inventory({"query": "x"}, "1", FakeWS()))
    assert out["status"] == "NO_MATCHES"


@pytest.mark.asyncio
async def test_search_pushes_carousel_and_returns_compact_context():
    product = {"id": 1, "name": "Shoes", "price": 10.0, "description": "d" * 200,
               "image_url": "", "category": "", "rating": 4.5, "stock": 3}
    executor, commerce, *_ = make_executor(products=[product])
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "app.services.ai_voice_service.ProductAccess.dump", side_effect=lambda p: p
    ):
        ws = FakeWS()
        out = json.loads(await executor.search_global_inventory({"query": "shoes"}, "1", ws))
    assert out["status"] == "SUCCESS"
    assert ws.sent and ws.sent[0]["type"] == "product_carousel"
    assert out["inventory"][0]["key_specs"].__len__() <= 100  # context is compacted


@pytest.mark.asyncio
async def test_search_ui_failure_does_not_break_voice_reply():
    product = {"id": 1, "name": "S", "price": 1.0, "description": "d",
               "image_url": "", "category": "", "rating": 0, "stock": 1}
    executor, *_ = make_executor(products=[product])
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "app.services.ai_voice_service.ProductAccess.dump", side_effect=lambda p: p
    ):
        out = json.loads(await executor.search_global_inventory({"query": "s"}, "1", FakeWS(fail=True)))
    assert out["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_cart_action_rejects_invalid_action():
    executor, *_ = make_executor()
    out = json.loads(await executor.execute_cart_action({"action": "EXPLODE"}, "1", FakeWS()))
    assert out["status"] == "FAILED"


@pytest.mark.asyncio
async def test_cart_action_add_requires_product_id():
    executor, *_ = make_executor()
    out = json.loads(await executor.execute_cart_action({"action": "ADD"}, "1", FakeWS()))
    assert "product_id" in out.get("error", "")


@pytest.mark.asyncio
async def test_cart_action_add_publishes_to_cart_queue():
    executor, _, _, rabbit = make_executor()
    out = json.loads(await executor.execute_cart_action({"action": "ADD", "product_id": 7}, "1", FakeWS()))
    assert out["status"] == "QUEUED"
    rabbit.publish.assert_awaited_once()
    payload, rk = rabbit.publish.await_args.args
    assert rk == "airdeliver.ai.cart.add"
    assert payload["product_id"] == 7 and payload["user_id"] == 1


@pytest.mark.asyncio
async def test_cart_action_checkout_uses_confirm_route():
    executor, _, _, rabbit = make_executor()
    out = json.loads(await executor.execute_cart_action({"action": "CHECKOUT"}, "1", FakeWS()))
    _, rk = rabbit.publish.await_args.args
    assert rk == "airdeliver.ai.order.confirm"


@pytest.mark.asyncio
async def test_cart_action_broker_failure_is_reported():
    executor, _, _, rabbit = make_executor()
    rabbit.publish = AsyncMock(side_effect=ConnectionError("broker down"))
    out = json.loads(await executor.execute_cart_action({"action": "CLEAR"}, "1", FakeWS()))
    assert out["status"] == "FAILED"


@pytest.mark.asyncio
async def test_phantom_product_empty_query_rejected():
    executor, *_ = make_executor()
    out = json.loads(await executor.verify_phantom_product({"query": ""}, "1"))
    assert "error" in out


@pytest.mark.asyncio
async def test_phantom_product_truncates_intel_and_warns_no_invention():
    executor, _, llm, _ = make_executor(web_intel="x" * 5000)
    out = json.loads(await executor.verify_phantom_product({"query": "iphone 18"}, "1"))
    assert out["status"] == "WEB_INTEL_RETRIEVED"
    assert len(out["data"]) <= 1000
    assert "NEVER invent specs" in out["advisory"]
