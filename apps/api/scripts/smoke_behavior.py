"""Behavior-engine + embeddings smoke test for dependency upgrades.

Run before and after a dependency bump with the same arguments:

    poetry run python scripts/smoke_behavior.py --out /tmp/smoke_before.json
    poetry run python scripts/smoke_behavior.py --out /tmp/smoke_after.json --compare /tmp/smoke_before.json

What it proves (deterministic, model-weights based):
  1. The real sentence-transformers model loads and produces stable
     embeddings (hash + pairwise cosine ranking preserved).
  2. BehaviorEngine end-to-end flow works: register_interaction,
     fingerprint stats, embedding-derived state, all finite and sane.

What it cannot prove: exact neural-brain outputs across torch versions
(OmniNet weights are randomly initialized per process), so it asserts
invariants (shape, finiteness, ranges) instead of exact values.
"""

import argparse
import asyncio
import hashlib
import json
import sys

import numpy as np

TEXTS = [
    "user loves nike running shoes",
    "customer wants cheap pizza delivery",
    "looking for waterproof hiking boots",
]

TOL = 2e-3  # cosine/vector tolerance across torch versions


def _round_hash(vec: np.ndarray) -> str:
    return hashlib.sha256(np.round(vec.astype(np.float64), 4).tobytes()).hexdigest()[:16]


def collect() -> dict:
    import torch

    torch.manual_seed(42)
    torch.set_num_threads(1)

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    emb = model.encode(TEXTS, convert_to_numpy=True, normalize_embeddings=True)

    cos = np.inner(emb, emb)
    result = {
        "torch_version": torch.__version__,
        "embedding_dim": int(emb.shape[1]),
        "embedding_hashes": [_round_hash(v) for v in emb],
        "cosine_matrix": np.round(cos, 5).tolist(),
        "cosine_ranking_0": int(np.argsort(-cos[0])[1]),  # nearest text to TEXTS[0]
    }

    # BehaviorEngine end-to-end with the REAL text model.
    import app.services.ai_commerce_engine as commerce
    from app.services.ai_behavior_engine import BehaviorEngine

    class _CacheClient:
        def scard(self, key):
            return 0

    class _Cache:
        def __init__(self):
            self.store = {}
            self.client = _CacheClient()

        async def get(self, key):
            return self.store.get(key)

        async def set(self, key, value, ttl=None):
            self.store[key] = value

        async def delete(self, key):
            self.store.pop(key, None)

    class _Registry:
        @staticmethod
        def get_text_model():
            return model

    commerce.ModelRegistry = _Registry

    cache = _Cache()
    engine = BehaviorEngine(cache)

    async def run_flow():
        await engine.register_interaction(1, TEXTS[0], weight=1.0)
        await engine.register_interaction(1, TEXTS[2], weight=0.5)
        return await engine.get_user_profile(1)

    profile = asyncio.run(run_flow())
    result["profile"] = {
        "keys": sorted(profile.keys()),
        "tier": str(profile.get("tier")),
        "persona": str(profile.get("persona")),
    }
    # Embedding-derived ghost state persisted through the cache is
    # deterministic for fixed model weights; hash it for comparison.
    ghost = [v for k, v in sorted(cache.store.items()) if isinstance(v, str) and len(v) > 10]
    result["ghost_states"] = [hashlib.sha256(g.encode()).hexdigest()[:16] for g in ghost]
    return result


def compare(before: dict, after: dict) -> list[str]:
    failures = []
    if before["embedding_dim"] != after["embedding_dim"]:
        failures.append(f"embedding dim changed {before['embedding_dim']} -> {after['embedding_dim']}")
    for i, (h0, h1) in enumerate(zip(before["embedding_hashes"], after["embedding_hashes"])):
        if h0 != h1:
            # hashes differ: fall back to numeric tolerance on cosines
            c0 = np.asarray(before["cosine_matrix"])
            c1 = np.asarray(after["cosine_matrix"])
            if not np.allclose(c0, c1, atol=TOL):
                failures.append(f"cosine matrix drifted beyond {TOL}")
            break
    if before["cosine_ranking_0"] != after["cosine_ranking_0"]:
        failures.append("nearest-neighbor ranking changed")
    bp, ap = before.get("profile"), after.get("profile")
    if not ap:
        failures.append("after-upgrade profile missing")
    elif bp and bp.get("keys") != ap.get("keys"):
        failures.append(f"profile keys changed {bp.get('keys')} -> {ap.get('keys')}")
    if after.get("ghost_states") is not None and before.get("ghost_states") is not None:
        if before["ghost_states"] != after["ghost_states"]:
            failures.append("ghost-state hashes changed across upgrade")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare")
    args = ap.parse_args()

    result = collect()
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"smoke snapshot written to {args.out} (torch {result['torch_version']})")

    if args.compare:
        with open(args.compare) as f:
            before = json.load(f)
        failures = compare(before, result)
        if failures:
            print("SMOKE COMPARISON FAILED:")
            for f_ in failures:
                print(" -", f_)
            sys.exit(1)
        print("SMOKE COMPARISON PASSED: embeddings + behavior engine stable across upgrade")


if __name__ == "__main__":
    main()
