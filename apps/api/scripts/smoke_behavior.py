"""Compare real embedding + behavior inference across dependency environments.

The default uses MiniLM and a reduced OmniNet to fit development machines.
It does NOT verify production GTE weights, the default production brain size,
or learned recommendation quality. OmniNet has no trained checkpoint here.

Run the SAME source revision and arguments in both dependency environments:
  python scripts/smoke_behavior.py --out /tmp/before.json
  python scripts/smoke_behavior.py --out /tmp/after.json --compare /tmp/before.json

Use --model Alibaba-NLP/gte-Qwen2-1.5B-instruct --full-brain only with
sufficient model storage/RAM. This may download model weights.
"""
import argparse
import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

TEXTS = ["user loves nike running shoes", "customer wants cheap pizza delivery",
         "looking for waterproof hiking boots"]
TOL = 2e-3


class MemoryCache:
    def __init__(self):
        self.store = {}
        self.lists = defaultdict(list)
        self.sets = defaultdict(set)
        self.client = self

    def pipeline(self):
        cache = self
        class Pipeline:
            def __init__(self):
                self.ops = []
            def __getattr__(self, name):
                def queue(*args, **kwargs):
                    self.ops.append((name, args, kwargs))
                    return self
                return queue
            async def execute(self):
                for name, args, kwargs in self.ops:
                    await getattr(cache, name)(*args, **kwargs)
        return Pipeline()

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl=None, ex=None):
        self.store[key] = value

    async def lpush(self, key, value):
        self.lists[key].insert(0, value)

    async def rpush(self, key, value):
        self.lists[key].append(value)

    async def lrange(self, key, start, end):
        return [v.decode("utf-8") if isinstance(v, bytes) else v
                for v in self.lists[key][start:None if end == -1 else end + 1]]

    async def ltrim(self, key, start, end):
        self.lists[key] = self.lists[key][start:None if end == -1 else end + 1]

    async def sadd(self, key, value):
        self.sets[key].add(value)

    async def scard(self, key):
        return len(self.sets[key])

    async def expire(self, key, ttl):
        pass


def collect(model_name, full_brain=False):
    import torch
    from sentence_transformers import SentenceTransformer
    import app.services.ai_commerce_engine as commerce
    import app.services.ai_behavior_engine as behavior

    torch.manual_seed(42)
    torch.set_num_threads(1)
    model = SentenceTransformer(model_name, device="cpu", trust_remote_code=False)
    embeddings = model.encode(TEXTS, convert_to_numpy=True, normalize_embeddings=True)
    dimension = int(embeddings.shape[1])
    config = behavior.OmniNetConfig() if full_brain else behavior.OmniNetConfig(
        internal_dim=24, intermediate_size=48, heads=4, layers=1, dropout=0,
        supported_dims={f"dim_{dimension}": dimension})
    cache = MemoryCache()
    engine = behavior.BehaviorEngine(cache, net_config=config)

    class Registry:
        def get_text_model(self):
            return model

    async def flow():
        with patch.object(commerce, "ModelRegistry", Registry), patch.object(
            behavior, "time", SimpleNamespace(time=lambda: 1700000010.0)
        ):
            for index, text in enumerate(TEXTS):
                await engine.register_interaction(1, text, weight=2.0 if index == 0 else 1.0)
            batch = []
            while not engine.synaptic_buffer.empty():
                packet = engine.synaptic_buffer.get_nowait()
                packet["ts"] = 1700000000.0 + len(batch)
                batch.append(packet)
            assert len(batch) == 3, "Registration did not produce three vectorized events"
            await engine._consolidate_memory(batch)
            while engine._background_tasks:
                await asyncio.gather(*list(engine._background_tasks))
            ghost_json = await cache.get(engine._key_ghost(1))
            assert ghost_json, "Consolidation/inference produced no ghost"
            ghost = json.loads(ghost_json)
            for kind in ("pos", "neg"):
                vector = np.asarray(ghost[kind])
                assert vector.shape == (config.internal_dim,)
                assert np.isfinite(vector).all()
                assert np.isclose(np.linalg.norm(vector), 1, atol=1e-5)
            profile = await engine.get_user_profile(1)
            assert "fallback" not in profile.get("meta", {}), "Profile used fallback"
            assert profile["metrics"]["neural_active"], "Profile did not see the generated ghost"
            await engine.stop()
            return ghost, profile

    ghost, profile = asyncio.run(flow())
    cos = np.inner(embeddings, embeddings)
    return {
        "schema_version": 2, "model_name": model_name, "torch_version": torch.__version__,
        "brain_profile": "production-default" if full_brain else "reduced-functional-test",
        "brain_config": config.model_dump(), "embedding_dim": dimension,
        "embedding_hashes": [hashlib.sha256(np.round(v.astype(np.float64), 4).tobytes()).hexdigest()[:16]
                             for v in embeddings],
        "cosine_matrix": cos.tolist(), "cosine_ranking_0": int(np.argsort(-cos[0])[1]),
        "ghost": {key: ghost[key] for key in ("pos", "neg", "src_dim")},
        "profile": profile,
        "scope": "Functional compatibility only. No trained behavioral checkpoint or production quality claim.",
    }


def compare(before, after):
    failures = []
    for key in ("schema_version", "model_name", "brain_config", "embedding_dim", "brain_profile"):
        if before.get(key) != after.get(key):
            failures.append(f"Incomparable or changed {key}")
    if before.get("schema_version") != 2:
        return failures + ["Old snapshots did not prove behavioral inference; rerun both environments"]
    if failures:
        return failures
    if not np.allclose(before["cosine_matrix"], after["cosine_matrix"], atol=TOL):
        failures.append("Embedding cosine matrix changed beyond tolerance")
    if before["cosine_ranking_0"] != after["cosine_ranking_0"]:
        failures.append("Nearest-neighbor ranking changed")
    for key in ("pos", "neg"):
        if not np.allclose(before["ghost"][key], after["ghost"][key], atol=TOL):
            failures.append(f"Behavior {key} vector changed beyond tolerance")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--compare")
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    parser.add_argument("--full-brain", action="store_true")
    args = parser.parse_args()
    result = collect(args.model, args.full_brain)
    with open(args.out, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"Snapshot written: {args.out}; model={args.model}; brain={result['brain_profile']}")
    if args.compare:
        with open(args.compare) as handle:
            failures = compare(json.load(handle), result)
        if failures:
            print("COMPARISON FAILED: " + "; ".join(failures))
            sys.exit(1)
        print("COMPARISON PASSED within the snapshot's stated model/configuration scope")


if __name__ == "__main__":
    main()
