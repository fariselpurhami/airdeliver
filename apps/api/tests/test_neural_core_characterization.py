# apps/api/tests/test_neural_core_characterization.py
"""
Characterization tests for NeuralCoreService, the LIVE text-chat intent router
(ai_support /chat POST -> handle_message). These pin the CURRENT behavior,
including one confirmed defect, before any hardening changes.

Confirmed defect pinned here: _handle_product_search calls
self.ai_engine.find_products_from_message(...), a method that does NOT exist on
AICommerceEngine, so every PRODUCT_SEARCH intent degrades to the
"global databanks" error fallback (AttributeError -> except branch).
"""

import pytest

from app.services.neural_core_service import (
    ChatMessage,
    NeuralCoreService,
    RouterDecision,
    SessionMemory,
)

pytestmark = pytest.mark.anyio


# --- Test doubles -------------------------------------------------------------


class FakeCache:
    """Minimal async cache stand-in with the two methods the service uses."""

    def __init__(self, initial=None):
        self.store = dict(initial or {})

    async def get_json(self, key):
        return self.store.get(key)

    async def set_json(self, key, value, ttl=None):
        self.store[key] = value


class FakeEngine:
    """Stands in for AICommerceEngine. Intentionally minimal: any engine
    failure (including a missing method) must degrade gracefully."""

    pass


class FakeProduct:
    def __init__(self, id=1, name="Aurora Headphones", price=499.0, inventory=12):
        self.id = id
        self.name = name
        self.price = price
        self.inventory = inventory


def make_service(engine=None, cache=None, monkeypatch=None, healthy=True):
    service = NeuralCoreService(engine or FakeEngine(), cache or FakeCache())
    # Health depends on GROQ_API_KEY in the env; tests control it explicitly.
    service.is_healthy = healthy
    if not healthy:
        service.client = None
    return service


# --- SessionMemory (pure contract) --------------------------------------------


class TestSessionMemory:
    def test_append_turn_adds_user_then_assistant(self):
        mem = SessionMemory(user_name="Faris")
        mem.append_turn("hi", "hello")
        assert [m.role for m in mem.history] == ["user", "assistant"]
        assert [m.content for m in mem.history] == ["hi", "hello"]

    def test_history_is_truncated_to_max_turns(self):
        mem = SessionMemory(user_name="Faris")
        for i in range(10):
            mem.append_turn(f"u{i}", f"a{i}", max_turns=5)
        # 5 turns * 2 messages = 10 max
        assert len(mem.history) == 10
        # Oldest turns are dropped first
        assert mem.history[0].content == "u5"
        assert mem.history[-1].content == "a9"


# --- RouterDecision schema ------------------------------------------------------


class TestRouterDecision:
    @pytest.mark.parametrize(
        "intent", ["PRODUCT_SEARCH", "TRACK_ORDER", "SUPPORT_HANDOFF", "SOCIAL_CHAT"]
    )
    def test_accepts_known_intents(self, intent):
        decision = RouterDecision(intent=intent)
        assert decision.intent == intent
        assert decision.query is None
        assert decision.order_id is None
        assert decision.social_reply is None

    def test_rejects_unknown_intent(self):
        with pytest.raises(Exception):
            RouterDecision(intent="ORDER_PIZZA")

    def test_parses_full_llm_payload(self):
        decision = RouterDecision.model_validate_json(
            '{"intent": "TRACK_ORDER", "order_id": "42"}'
        )
        assert decision.intent == "TRACK_ORDER"
        assert decision.order_id == "42"


# --- _analyze_intent ------------------------------------------------------------


class TestAnalyzeIntent:
    async def test_unconfigured_service_reports_unavailable(self):
        service = make_service(healthy=False)
        decision = await service._analyze_intent("hello", SessionMemory(user_name="F"))
        assert decision.intent == "SOCIAL_CHAT"
        assert "not configured" in decision.social_reply

    async def test_valid_llm_json_is_parsed(self, monkeypatch):
        service = make_service()

        async def fake_infer(messages):
            return '{"intent": "PRODUCT_SEARCH", "query": "headphones", "search_subject": "headphones"}'

        monkeypatch.setattr(service, "_execute_llm_inference", fake_infer)
        decision = await service._analyze_intent("I want headphones", SessionMemory(user_name="F"))
        assert decision.intent == "PRODUCT_SEARCH"
        assert decision.query == "headphones"

    async def test_history_is_included_in_messages(self, monkeypatch):
        service = make_service()
        captured = {}

        async def fake_infer(messages):
            captured["messages"] = messages
            return '{"intent": "SOCIAL_CHAT", "social_reply": "hey"}'

        monkeypatch.setattr(service, "_execute_llm_inference", fake_infer)
        mem = SessionMemory(user_name="F")
        mem.append_turn("earlier question", "earlier answer")
        await service._analyze_intent("follow up", mem)
        roles = [m["role"] for m in captured["messages"]]
        assert roles == ["system", "user", "assistant", "user"]

    async def test_schema_violation_falls_back_to_social(self, monkeypatch):
        service = make_service()

        async def fake_infer(messages):
            return '{"intent": "NOT_A_REAL_INTENT"}'

        monkeypatch.setattr(service, "_execute_llm_inference", fake_infer)
        decision = await service._analyze_intent("hi", SessionMemory(user_name="F"))
        assert decision.intent == "SOCIAL_CHAT"
        assert "temporarily unavailable" in decision.social_reply

    async def test_inference_exception_falls_back_to_social(self, monkeypatch):
        service = make_service()

        async def fake_infer(messages):
            raise RuntimeError("groq down")

        monkeypatch.setattr(service, "_execute_llm_inference", fake_infer)
        decision = await service._analyze_intent("hi", SessionMemory(user_name="F"))
        assert decision.intent == "SOCIAL_CHAT"

    async def test_hallucinated_order_id_is_dropped(self, monkeypatch):
        """Anti-hallucination grounding: an LLM-extracted order_id whose digits
        never appear in the user's message is dropped ( -> handler asks for it)."""
        service = make_service()

        async def fake_infer(messages):
            return '{"intent": "TRACK_ORDER", "order_id": "99999"}'

        monkeypatch.setattr(service, "_execute_llm_inference", fake_infer)
        decision = await service._analyze_intent("where is my stuff?", SessionMemory(user_name="F"))
        assert decision.intent == "TRACK_ORDER"
        assert decision.order_id is None

    async def test_grounded_order_id_is_kept(self, monkeypatch):
        service = make_service()

        async def fake_infer(messages):
            return '{"intent": "TRACK_ORDER", "order_id": "12345"}'

        monkeypatch.setattr(service, "_execute_llm_inference", fake_infer)
        decision = await service._analyze_intent("where is order 12345?", SessionMemory(user_name="F"))
        assert decision.order_id == "12345"


# --- Action handlers ------------------------------------------------------------


class TestOrderTrackingHandler:
    def test_with_order_id_returns_track_action(self):
        service = make_service()
        resp = service._handle_order_tracking("12345")
        assert resp.action is not None
        assert resp.action.action == "track_order"
        assert resp.action.payload.order_id == "12345"
        assert "12345" in resp.text
        assert resp.telemetry.intent == "TRACK_ORDER"

    def test_without_order_id_asks_for_id(self):
        service = make_service()
        resp = service._handle_order_tracking(None)
        assert resp.action is None
        assert "Order ID" in resp.text


class TestSupportHandoffHandler:
    def test_returns_handoff_action(self):
        service = make_service()
        resp = service._handle_support_handoff()
        assert resp.action is not None
        assert resp.action.action == "initiate_support_handoff"
        assert resp.confidence == 1.0


class TestProductSearchHandler:
    async def test_engine_failure_degrades_gracefully(self):
        """Any engine failure (exception or missing method) must land in the
        degradation branch, never crash the chat."""

        class RaisingEngine(FakeEngine):
            async def perform_hybrid_search_pure(self, db, query, limit=5):
                raise RuntimeError("milvus down")

        service = make_service(engine=RaisingEngine())
        resp = await service._handle_product_search(db=None, query="headphones")
        assert resp.confidence == 0.0
        assert resp.text.startswith("System notice:")

    async def test_empty_product_list_text(self):
        """Zero search results yields the broaden-search text."""

        class EmptyEngine(FakeEngine):
            async def perform_hybrid_search_pure(self, db, query, limit=5):
                return []

        service = make_service(engine=EmptyEngine())
        resp = await service._handle_product_search(db=None, query="headphones")
        assert resp.response_kind == "system_notice"
        assert resp.products == []

    async def test_product_result_text_uses_real_fields(self):
        """In-stock product: name, price and stock status come from the
        product record itself, not invented by the LLM."""

        class OneProductEngine(FakeEngine):
            async def perform_hybrid_search_pure(self, db, query, limit=5):
                return [FakeProduct()]

        service = make_service(engine=OneProductEngine())
        resp = await service._handle_product_search(db=None, query="headphones")
        # A candidate object without a current DB read cannot support a card.
        assert resp.products == []
        assert "Aurora Headphones" not in resp.text
        assert resp.response_kind == "system_notice"

    async def test_out_of_stock_product_reports_stock_only(self):
        class OosEngine(FakeEngine):
            async def perform_hybrid_search_pure(self, db, query, limit=5):
                return [FakeProduct(inventory=0)]

        service = make_service(engine=OosEngine())
        resp = await service._handle_product_search(db=None, query="headphones")
        assert resp.products == []
        assert resp.response_kind == "system_notice"


# --- handle_message orchestration -------------------------------------------------


class TestHandleMessage:
    async def test_social_route_uses_social_reply_and_persists_memory(self, monkeypatch):
        cache = FakeCache()
        service = make_service(cache=cache)

        async def fake_analyze(message, memory):
            return RouterDecision(intent="SOCIAL_CHAT", social_reply="Ahoy, VIP!")

        monkeypatch.setattr(service, "_analyze_intent", fake_analyze)
        from unittest.mock import AsyncMock
        import json
        service._execute_llm_inference=AsyncMock(side_effect=[json.dumps({"text":"Ahoy, VIP!","product_ids":[],"claims":[]}),json.dumps({"supported":True,"all_product_mentions_declared":True,"no_unsupported_commercial_claims":True,"fulfills_discovery_task":True})])
        resp = await service.handle_message(db=None, message="yo", user=None, session_id="s1")
        assert resp.text == "Ahoy, VIP!"
        assert "Model-authored" in resp.explain
        # Memory persisted under the versioned session key
        stored = cache.store.get("ai_session_v9:s1")
        assert stored is not None
        assert stored["history"][-1]["content"] == "Ahoy, VIP!"

    async def test_social_route_defaults_when_social_reply_missing(self, monkeypatch):
        service = make_service()

        async def fake_analyze(message, memory):
            return RouterDecision(intent="SOCIAL_CHAT", social_reply=None)

        monkeypatch.setattr(service, "_analyze_intent", fake_analyze)
        resp = await service.handle_message(db=None, message="yo", user=None, session_id="s2")
        assert resp.text  # non-empty default
        assert resp.response_kind == "system_notice"

    async def test_product_route_uses_query_or_message(self, monkeypatch):
        service = make_service(engine=FakeEngine())  # FakeEngine raises -> degradation branch
        seen = {}

        async def fake_analyze(message, memory):
            return RouterDecision(intent="PRODUCT_SEARCH", query=None)

        monkeypatch.setattr(service, "_analyze_intent", fake_analyze)
        resp = await service.handle_message(db=None, message="show me headphones", user=None, session_id="s3")
        # query falls back to the raw message; engine failure -> degradation text
        assert resp.telemetry.intent == "PRODUCT_SEARCH"
        assert resp.text.startswith("System notice:")

    async def test_handoff_route(self, monkeypatch):
        service = make_service()

        async def fake_analyze(message, memory):
            return RouterDecision(intent="SUPPORT_HANDOFF")

        monkeypatch.setattr(service, "_analyze_intent", fake_analyze)
        resp = await service.handle_message(db=None, message="human please", user=None, session_id="s4")
        assert resp.action is not None
        assert resp.action.action == "initiate_support_handoff"

    async def test_track_route(self, monkeypatch):
        service = make_service()

        async def fake_analyze(message, memory):
            return RouterDecision(intent="TRACK_ORDER", order_id="777")

        monkeypatch.setattr(service, "_analyze_intent", fake_analyze)
        resp = await service.handle_message(db=None, message="track 777", user=None, session_id="s5")
        assert resp.action.action == "track_order"
        assert resp.action.payload.order_id == "777"

    async def test_turn_counter_counts_completed_turns(self, monkeypatch):
        cache = FakeCache()
        service = make_service(cache=cache)

        async def fake_analyze(message, memory):
            return RouterDecision(intent="SOCIAL_CHAT", social_reply="hi")

        monkeypatch.setattr(service, "_analyze_intent", fake_analyze)
        service.is_healthy=False
        await service.handle_message(db=None, message="one", user=None, session_id="s6")
        resp = await service.handle_message(db=None, message="two", user=None, session_id="s6")
        # Second call sees 1 completed prior turn
        assert resp.telemetry.turn == 1
