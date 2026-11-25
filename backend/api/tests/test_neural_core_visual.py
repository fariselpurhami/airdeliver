# backend/api/tests/test_neural_core_visual.py
"""
Tests for the NeuralCoreService visual-search path (image-based product
search). The live chat endpoint accepts an optional base64 image; when
present, the service must route to the engine's visual vector search and
answer strictly from the inventory records returned - never invented
products, prices or availability.
"""

import pytest

from app.services.neural_core_service import NeuralCoreService

pytestmark = pytest.mark.anyio


class FakeCache:
    def __init__(self, initial=None):
        self.store = dict(initial or {})

    async def get_json(self, key):
        return self.store.get(key)

    async def set_json(self, key, value, ttl=None):
        self.store[key] = value


class FakeProduct:
    def __init__(self, id=1, name="Aurora Headphones", price=499.0, inventory=12):
        self.id = id
        self.name = name
        self.price = price
        self.inventory = inventory


class FakeVisualEngine:
    """Records calls and serves canned visual-search results."""

    def __init__(self, results=None, error=None):
        self.results = results if results is not None else [FakeProduct()]
        self.error = error
        self.calls = []

    async def search_by_image_vector(self, image_input, limit=8):
        self.calls.append({"image_input": image_input, "limit": limit})
        if self.error is not None:
            raise self.error
        return self.results


class ExplodingRouterEngine(FakeVisualEngine):
    """If the LLM intent router is touched for an image message, fail."""

    pass


def make_service(engine):
    service = NeuralCoreService(engine, FakeCache())
    service.is_healthy = True
    return service


VALID_IMAGE = "aGVsbG8gd29ybGQ="  # base64 payload (content irrelevant; engine is faked)


class TestVisualRouting:
    async def test_image_message_routes_to_visual_search(self):
        engine = FakeVisualEngine()
        service = make_service(engine)

        response = await service.handle_message(
            db=None,
            message="",
            user=None,
            session_id="session-visual-1",
            image_base64=VALID_IMAGE,
        )

        assert len(engine.calls) == 1
        assert engine.calls[0]["image_input"] == VALID_IMAGE
        assert response.products == []
        assert response.response_kind == "system_notice"
        assert response.telemetry.intent == "VISUAL_SEARCH"

    async def test_image_search_does_not_call_llm_router(self, monkeypatch):
        engine = FakeVisualEngine()
        service = make_service(engine)

        async def explode(*args, **kwargs):
            raise AssertionError("LLM router must not run for image messages")

        monkeypatch.setattr(service, "_analyze_intent", explode)
        response = await service.handle_message(
            db=None,
            message="",
            user=None,
            session_id="session-visual-2",
            image_base64=VALID_IMAGE,
        )
        assert response.response_kind == "system_notice"

    async def test_caption_is_not_required(self):
        engine = FakeVisualEngine()
        service = make_service(engine)
        response = await service.handle_message(
            db=None, message="", user=None,
            session_id="session-visual-3", image_base64=VALID_IMAGE,
        )
        assert response.text.strip()


class TestVisualGrounding:
    async def test_answer_uses_real_product_fields(self):
        engine = FakeVisualEngine(results=[FakeProduct(name="Volt Charger", price=59.5, inventory=3)])
        service = make_service(engine)
        response = await service.handle_message(
            db=None, message="", user=None,
            session_id="session-visual-4", image_base64=VALID_IMAGE,
        )
        # An index result without a current DB row is not product evidence.
        assert response.products == []
        assert "Volt Charger" not in response.text

    async def test_out_of_stock_product_is_reported_without_restock_promise(self):
        engine = FakeVisualEngine(results=[FakeProduct(inventory=0)])
        service = make_service(engine)
        response = await service.handle_message(
            db=None, message="", user=None,
            session_id="session-visual-5", image_base64=VALID_IMAGE,
        )
        assert response.products == []
        assert response.response_kind == "system_notice"

    async def test_no_matches_is_honest_no_invention(self):
        engine = FakeVisualEngine(results=[])
        service = make_service(engine)
        response = await service.handle_message(
            db=None, message="", user=None,
            session_id="session-visual-6", image_base64=VALID_IMAGE,
        )
        assert "Aurora" not in response.text
        assert response.confidence < 0.5

    async def test_engine_failure_degrades_gracefully(self):
        engine = FakeVisualEngine(error=RuntimeError("milvus down"))
        service = make_service(engine)
        response = await service.handle_message(
            db=None, message="", user=None,
            session_id="session-visual-7", image_base64=VALID_IMAGE,
        )
        assert response.confidence == 0.0
        assert response.text.strip()
