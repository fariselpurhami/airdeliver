"""Readiness warmup for local text encoders, separate from request deadlines.

Native inference cannot be killed safely in a Python thread. A timeout rejects
readiness and publication immediately; already-running native work may drain.
"""
from dataclasses import dataclass
import logging
import time

import numpy as np

logger = logging.getLogger(__name__)
STARTUP_MODEL_BUDGET_SECONDS = 360.0


class TextEmbeddingWarmupError(RuntimeError):
    pass


@dataclass(frozen=True)
class WarmupPolicy:
    budget_seconds: float = 240.0
    sample_max_seconds: float = 5.0
    consecutive_samples: int = 2
    max_attempts: int = 8

    def __post_init__(self):
        if (self.budget_seconds <= 0 or self.sample_max_seconds <= 0
                or self.consecutive_samples < 2 or self.max_attempts < self.consecutive_samples):
            raise ValueError("Invalid text embedding warmup policy")


def warm_text_encoder(model, dimension, *, policy=WarmupPolicy(), clock=time.monotonic,
                      rejected=None):
    """Require consecutive fast, valid encodes before publishing the model.

    Uses the existing raw-query encode contract. This does not select a prompt,
    alter normalization, or change the model's configured sequence length.
    """
    started = clock()
    consecutive = 0
    durations = []
    for attempt in range(1, policy.max_attempts + 1):
        if (rejected is not None and rejected.is_set()) or clock() - started >= policy.budget_seconds:
            raise TextEmbeddingWarmupError("Text embedding warmup budget exhausted")
        sample_started = clock()
        vector = np.asarray(model.encode(
            "I need a warm fleece jacket for cool weather", convert_to_numpy=True))
        elapsed = clock() - sample_started
        durations.append(round(elapsed, 4))
        if (vector.shape != (dimension,) or not np.isfinite(vector).all()
                or not np.any(vector)):
            raise TextEmbeddingWarmupError("Text embedding warmup returned an invalid vector")
        if (rejected is not None and rejected.is_set()) or clock() - started > policy.budget_seconds:
            raise TextEmbeddingWarmupError("Text embedding warmup budget exhausted")
        consecutive = consecutive + 1 if elapsed <= policy.sample_max_seconds else 0
        logger.info("text embedding warmup sample attempt=%d seconds=%.4f consecutive=%d",
                    attempt, elapsed, consecutive)
        if consecutive >= policy.consecutive_samples:
            return {"state": "ready", "sample_seconds": durations,
                    "elapsed_seconds": round(clock() - started, 4)}
    raise TextEmbeddingWarmupError("Text embedding warmup did not reach consecutive fast samples")
