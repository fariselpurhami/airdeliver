"""Exercise real tensors and the Redis decode_responses contract with a small brain."""
import asyncio
import json
from collections import defaultdict

import numpy as np
import pytest
import torch

from app.services.ai_behavior_engine import BehaviorEngine, OmniNet, OmniNetConfig


def tiny_config():
    return OmniNetConfig(internal_dim=24, intermediate_size=48, heads=4, layers=1,
                         dropout=0, supported_dims={"dim_384": 384, "dim_24": 24})


class MemoryPipeline:
    def __init__(self, cache):
        self.cache = cache
        self.ops = []

    def __getattr__(self, name):
        def enqueue(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            return self
        return enqueue

    async def execute(self):
        for name, args, kwargs in self.ops:
            await getattr(self.cache, name)(*args, **kwargs)
        return [True] * len(self.ops)


class DecodingCache:
    """Mimic Redis decode_responses=True. Raw binary stream packets must fail."""
    def __init__(self):
        self.store = {}
        self.lists = defaultdict(list)
        self.sets = defaultdict(set)
        self.client = self

    def pipeline(self):
        return MemoryPipeline(self)

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl=None, ex=None):
        self.store[key] = value

    async def get_json(self, key):
        value = await self.get(key)
        return json.loads(value) if value else None

    async def lpush(self, key, value):
        self.lists[key].insert(0, value)

    async def rpush(self, key, value):
        self.lists[key].append(value)

    async def ltrim(self, key, start, end):
        self.lists[key] = self.lists[key][start: None if end == -1 else end + 1]

    async def lrange(self, key, start, end):
        values = self.lists[key][start: None if end == -1 else end + 1]
        return [value.decode("utf-8") if isinstance(value, bytes) else value for value in values]

    async def sadd(self, key, value):
        self.sets[key].add(value)

    async def scard(self, key):
        return len(self.sets[key])

    async def expire(self, key, ttl):
        return True


def test_omni_forward_generates_its_causal_mask():
    net = OmniNet(tiny_config()).train()
    pos, neg = net(torch.ones(1, 3, 384), torch.zeros(1, 3, dtype=torch.long),
                   torch.zeros(1, 3), input_dim=384)
    assert pos.shape == neg.shape == (1, 24)
    assert torch.isfinite(pos).all() and torch.isfinite(neg).all()


@pytest.mark.asyncio
async def test_real_consolidation_creates_finite_nonfallback_ghost(monkeypatch):
    import app.services.ai_behavior_engine as module
    monkeypatch.setattr(module, "OmniNetConfig", tiny_config)
    cache = DecodingCache()
    engine = BehaviorEngine(cache, allow_untrained_inference=True)
    await engine.start()
    for index in range(3):
        await engine.track_interaction(7, "view", {"vec": np.linspace(0.01, 1, 384).tolist(), "id": index + 1, "price": 20})
    for _ in range(100):
        if await cache.get(engine.ghost_key(7)):
            break
        await asyncio.sleep(0.01)
    await engine.stop()
    ghost = await cache.get_json(engine.ghost_key(7))
    assert ghost, "No ghost was produced by the real queue/consolidation/inference flow"
    assert len(ghost["pos"]) == len(ghost["neg"]) == 24
    assert np.isfinite(ghost["pos"]).all()
    assert np.isclose(np.linalg.norm(ghost["pos"]), 1, atol=1e-5)
    profile = await engine.get_user_profile(7)
    assert "fallback" not in profile.get("meta", {})
    assert profile["metrics"]["neural_active"] is True
    assert not engine._background_tasks
