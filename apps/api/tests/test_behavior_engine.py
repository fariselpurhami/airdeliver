# apps/api/tests/test_behavior_engine.py
"""Locks in the NLU <-> BehaviorEngine seam: register_interaction must convert
text signals into vectorized track_interaction events (previously the method
did not exist and NLU signals were silently dropped by a hasattr guard)."""
import numpy as np
import pytest

from app.services.ai_behavior_engine import BehaviorEngine


class _FakeCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl=None):
        pass

    async def delete(self, key):
        pass


class _FakeModel:
    def encode(self, text, convert_to_numpy=True):
        return np.ones(1536, dtype=np.float32)


class _FakeRegistry:
    def get_text_model(self):
        return _FakeModel()


@pytest.mark.asyncio
async def test_register_interaction_maps_weight_and_embeds(monkeypatch):
    import app.services.ai_commerce_engine as commerce

    monkeypatch.setattr(commerce, "ModelRegistry", _FakeRegistry)

    engine = BehaviorEngine(_FakeCache())
    from unittest.mock import AsyncMock
    engine._learning_generation=AsyncMock(return_value=('consent','0'))
    calls = []

    async def _capture(user_id, interaction_type, metadata):
        calls.append((user_id, interaction_type, metadata))

    monkeypatch.setattr(engine, "track_interaction", _capture)

    await engine.register_interaction(7, "audio wireless earbuds", weight=2.0)
    await engine.register_interaction(7, "cases phone cover", weight=1.0)
    await engine.register_interaction(7, "", weight=1.0)

    assert [c[1] for c in calls] == ["search_hit", "view"]
    assert all(len(c[2]["vec"]) == 1536 for c in calls)
    assert all(c[0] == 7 for c in calls)


@pytest.mark.asyncio
async def test_register_interaction_survives_model_failure(monkeypatch):
    import app.services.ai_commerce_engine as commerce

    class _BoomRegistry:
        def get_text_model(self):
            raise RuntimeError("model unavailable")

    monkeypatch.setattr(commerce, "ModelRegistry", _BoomRegistry)
    engine = BehaviorEngine(_FakeCache())
    from unittest.mock import AsyncMock
    engine._learning_generation=AsyncMock(return_value=('consent','0'))
    # Must not raise: behavioral learning degrades silently, never breaks chat.
    await engine.register_interaction(7, "anything", weight=1.0)


@pytest.fixture(autouse=True)
def reduced_test_brain(monkeypatch):
    """Test adapters with real tensors without allocating the production brain."""
    import app.services.ai_behavior_engine as module
    config = module.OmniNetConfig(internal_dim=24, intermediate_size=48, heads=4,
                                 layers=1, supported_dims={"dim_1536": 1536})
    monkeypatch.setattr(module, "OmniNetConfig", lambda: config)
