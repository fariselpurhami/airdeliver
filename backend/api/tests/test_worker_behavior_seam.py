# backend/api/tests/test_worker_behavior_seam.py
"""Worker -> BehaviorEngine seam: analytics consumers exist, and behavior
events carrying a product id are enriched with the product's Milvus embedding
before reaching the OmniNet."""
from types import SimpleNamespace

import pytest

from app.services.orchestration.worker_entrypoint import WorkerRuntime


class _FakeBehavior:
    def __init__(self):
        self.calls = []

    async def track_interaction(self, user_id, action, metadata):
        self.calls.append((user_id, action, metadata))


class _FakeMilvus:
    def get(self, collection_name, ids):
        return [{"id": ids[0], "vector": [0.1] * 1536}]


def _runtime_with(behavior=None, commerce=None):
    rt = WorkerRuntime.__new__(WorkerRuntime)
    rt.services = SimpleNamespace(behavior=behavior, commerce=commerce)
    return rt


@pytest.mark.asyncio
async def test_track_behavior_enriches_with_milvus_vector():
    behavior = _FakeBehavior()
    commerce = SimpleNamespace(milvus_client=_FakeMilvus(), milvus_product_text_col="col")
    rt = _runtime_with(behavior, commerce)

    await rt.track_behavior(9, "cart", {"id": 555, "action": "add"})

    _, action, meta = behavior.calls[0]
    assert action == "cart"
    assert len(meta["vec"]) == 1536
    assert meta["id"] == 555


@pytest.mark.asyncio
async def test_track_behavior_survives_milvus_failure():
    class _BoomMilvus:
        def get(self, collection_name, ids):
            raise RuntimeError("milvus down")

    behavior = _FakeBehavior()
    commerce = SimpleNamespace(milvus_client=_BoomMilvus(), milvus_product_text_col="col")
    rt = _runtime_with(behavior, commerce)

    await rt.track_behavior(9, "discard", {"id": 1})
    assert "vec" not in behavior.calls[0][2]


@pytest.mark.asyncio
async def test_removal_recovery_maps_to_discard():
    behavior = _FakeBehavior()
    rt = _runtime_with(behavior, None)

    async def _noop(**kwargs):
        return None

    rt.wait_for_readiness = _noop
    await rt.removal_recovery_handler_impl({"user_id": 3, "removed_product_id": 42, "action": "remove"})

    user_id, action, meta = behavior.calls[0]
    assert (user_id, action) == (3, "discard")
    assert meta["id"] == 42


@pytest.mark.asyncio
async def test_analytics_conversion_maps_to_buy_with_price():
    behavior = _FakeBehavior()
    rt = _runtime_with(behavior, None)

    async def _noop(**kwargs):
        return None

    rt.wait_for_readiness = _noop
    await rt.analytics_conversion_handler_impl({"user_id": 3, "order_id": 9, "revenue": "1200.50"})

    user_id, action, meta = behavior.calls[0]
    assert (user_id, action) == (3, "buy")
    assert meta["price"] == 1200.50
