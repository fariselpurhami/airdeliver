"""Offline, user-disjoint training/evaluation for the existing OmniNet.

This job only writes candidate artifacts. It never changes a serving model,
contacts an external provider or approves a model for production.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch
import torch.nn.functional as F
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.ai_behavior_engine import ACTION_MAP, OmniNet, OmniNetConfig
from app.services.behavior_checkpoint import BehaviorManifest, file_sha256, load_behavior_checkpoint, save_behavior_checkpoint

POSITIVE_ACTIONS = {"cart", "checkout", "buy", "search_hit"}


class InteractionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    event_id: str = Field(min_length=1, max_length=128)
    item_id: str = Field(min_length=1, max_length=128)
    action: str
    timestamp: float = Field(gt=0)
    vector: list[float] = Field(min_length=4, max_length=4096)

    @model_validator(mode="after")
    def known_action(self):
        if self.action not in ACTION_MAP:
            raise ValueError("Unknown interaction action")
        return self


class InteractionSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: str = Field(min_length=1, max_length=128)
    embedding_source: str = Field(min_length=3, max_length=256)
    source: Literal["synthetic", "real"]
    events: list[InteractionEvent] = Field(min_length=4, max_length=256)

    @model_validator(mode="after")
    def ordered_homogeneous_sequence(self):
        if "@" not in self.embedding_source or not all(self.embedding_source.rsplit("@", 1)):
            raise ValueError("Embedding identity must include a revision")
        if len({len(event.vector) for event in self.events}) != 1:
            raise ValueError("Mixed embedding dimensions in one session")
        if any(a.timestamp > b.timestamp for a, b in zip(self.events, self.events[1:])):
            raise ValueError("Events must be time ordered")
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("Duplicate event ID")
        return self


@dataclass
class SequenceExample:
    subject_id: str
    context: list[InteractionEvent]
    target: InteractionEvent

    @property
    def head(self) -> str:
        return "negative" if self.target.action == "discard" else "positive"


def subject_partition(subject_id: str) -> str:
    """Stable across dataset growth and warm starts. Never reshuffle users."""
    bucket = int(hashlib.sha256(subject_id.encode()).hexdigest()[:8], 16) % 100
    return "train" if bucket < 70 else ("validation" if bucket < 85 else "test")


def load_interaction_dataset(path: str | Path) -> list[InteractionSession]:
    source = Path(path)
    if not source.is_file() or not 0 < source.stat().st_size <= 512 * 1024 ** 2:
        raise ValueError("Dataset must be a nonempty local JSONL file, at most 512 MiB")
    sessions, event_ids = [], set()
    with source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if len(line) > 16 * 1024 ** 2 or line_number > 10000:
                raise ValueError("Dataset exceeds bounded record limits")
            if not line.strip():
                continue
            session = InteractionSession.model_validate_json(line)
            for event in session.events:
                if event.event_id in event_ids:
                    raise ValueError("Event ID appears more than once in the dataset")
                event_ids.add(event.event_id)
            sessions.append(session)
    if not sessions:
        raise ValueError("Dataset has no sessions")
    identities = {(item.embedding_source, len(item.events[0].vector)) for item in sessions}
    if len(identities) != 1:
        raise ValueError("Train each embedding source/dimension in a separate candidate job")
    return sessions


def split_examples(sessions: list[InteractionSession], context_length: int = 16):
    if not 3 <= context_length <= 64:
        raise ValueError("Context length must be between 3 and 64")
    splits = {name: [] for name in ("train", "validation", "test")}
    subjects = {name: set() for name in splits}
    for session in sessions:
        partition = subject_partition(session.subject_id)
        subjects[partition].add(session.subject_id)
        for index in range(3, len(session.events)):
            if session.events[index].action not in POSITIVE_ACTIONS | {"discard"}:
                continue
            splits[partition].append(SequenceExample(session.subject_id, session.events[max(0, index - context_length):index], session.events[index]))
    if any(not examples for examples in splits.values()):
        raise ValueError("Need nonempty training, validation and test partitions with distinct subjects")
    return splits, subjects


def context_tensors(examples: list[SequenceExample], device: torch.device):
    # Batches are bucketed by context length, so no fake padding enters the
    # transformer. Deltas stop at the latest observed event, not target time.
    vectors = torch.tensor([[event.vector for event in example.context] for example in examples], dtype=torch.float32, device=device)
    actions = torch.tensor([[ACTION_MAP[event.action] for event in example.context] for example in examples], dtype=torch.long, device=device)
    times = torch.tensor([[example.context[-1].timestamp - event.timestamp for event in example.context] for example in examples], dtype=torch.float32, device=device)
    return vectors, actions, times


def adapted_candidates(model: OmniNet, vectors: torch.Tensor, dimension: int) -> torch.Tensor:
    if dimension != model.config.internal_dim:
        vectors = model.input_adapters[f"dim_{dimension}"](vectors)
        vectors = F.layer_norm(vectors, (model.config.internal_dim,), eps=model.config.layer_norm_eps)
    return F.normalize(vectors, dim=-1)


def evaluate_ranking(model: OmniNet, examples: list[SequenceExample], device: torch.device) -> dict[str, float]:
    positives = [example for example in examples if example.head == "positive"]
    if not positives:
        raise ValueError("Evaluation needs positive held-out outcomes")
    catalog = {}
    for example in examples:
        for event in [*example.context, example.target]:
            if event.item_id in catalog and catalog[event.item_id] != event.vector:
                raise ValueError("One item has inconsistent vectors within the evaluation snapshot")
            catalog[event.item_id] = event.vector
    if len(catalog) < 2:
        raise ValueError("Evaluation needs multiple distinct candidates")
    ids = sorted(catalog)
    lookup = {item: index for index, item in enumerate(ids)}
    raw_candidates = torch.tensor([catalog[item] for item in ids], dtype=torch.float32, device=device)
    dimension = raw_candidates.shape[1]
    model.eval()
    ndcg = reciprocal = baseline_ndcg = baseline_reciprocal = 0.0
    with torch.inference_mode():
        candidates = adapted_candidates(model, raw_candidates, dimension)
        raw_normalized = F.normalize(raw_candidates, dim=-1)
        for example in positives:
            vectors, actions, times = context_tensors([example], device)
            positive, negative = model(vectors, actions, times, input_dim=dimension)
            scores = (positive @ candidates.T - 0.4 * (negative @ candidates.T))[0]
            latest = next((event for event in reversed(example.context) if event.action != "discard"), example.context[-1])
            baseline = F.normalize(torch.tensor(latest.vector, dtype=torch.float32, device=device), dim=0) @ raw_normalized.T
            target = lookup[example.target.item_id]
            # Stable index tie-breaking avoids optimistic handling of ties.
            rank = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), i)).index(target) + 1
            baseline_rank = sorted(range(len(ids)), key=lambda i: (-float(baseline[i]), i)).index(target) + 1
            if rank <= 10:
                ndcg += 1 / math.log2(rank + 1)
                reciprocal += 1 / rank
            if baseline_rank <= 10:
                baseline_ndcg += 1 / math.log2(baseline_rank + 1)
                baseline_reciprocal += 1 / baseline_rank
    count = len(positives)
    return {"ndcg_at_10": ndcg / count, "mrr_at_10": reciprocal / count,
            "baseline_ndcg_at_10": baseline_ndcg / count, "baseline_mrr_at_10": baseline_reciprocal / count,
            "evaluated_examples": float(count), "candidate_count": float(len(ids))}


def train_behavior_candidate(
    dataset_path: str | Path, output_path: str | Path, config: OmniNetConfig, *,
    model_version: str, epochs: int = 3, batch_size: int = 8,
    context_length: int = 16, seed: int = 42, learning_rate: float = 3e-4,
    warm_start: str | Path | None = None,
) -> dict:
    if not 1 <= epochs <= 100 or not 2 <= batch_size <= 64 or not 0 < learning_rate <= 0.01:
        raise ValueError("Invalid bounded training parameters")
    target = Path(output_path)
    if target.exists() or Path(str(target) + ".metrics.json").exists():
        raise ValueError("Candidate output already exists; choose a new versioned path")
    sessions = load_interaction_dataset(dataset_path)
    splits, subjects = split_examples(sessions, context_length)
    dimension = len(sessions[0].events[0].vector)
    source_identity = {f"dim_{dimension}": sessions[0].embedding_source}
    if f"dim_{dimension}" not in config.supported_dims:
        raise ValueError("Dataset dimension has no model adapter")
    torch.manual_seed(seed)
    randomizer = random.Random(seed)
    device = torch.device("cpu")
    model = OmniNet(config).to(device)
    if warm_start:
        previous = load_behavior_checkpoint(warm_start, expected_actions=ACTION_MAP, expected_embeddings=source_identity)
        if previous.manifest.architecture != config.model_dump():
            raise ValueError("Warm-start architecture differs from this job")
        if previous.manifest.split_strategy != "user_disjoint_time_ordered":
            raise ValueError("Warm start requires the stable subject split contract")
        model.load_state_dict(previous.state_dict, strict=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    buckets = defaultdict(list)
    for example in splits["train"]:
        buckets[(len(example.context), example.head)].append(example)
    if not {"positive", "negative"} <= {key[1] for key in buckets}:
        raise ValueError("Training needs positive outcomes and explicit discard outcomes for both heads")
    best_score, best_state, history = -1.0, None, []
    steps = {"positive": 0, "negative": 0}
    for epoch in range(epochs):
        model.train()
        losses = []
        groups = list(buckets.values())
        randomizer.shuffle(groups)
        for group in groups:
            order = list(group)
            randomizer.shuffle(order)
            for start in range(0, len(order), batch_size):
                # Repeated target items are not false in-batch negatives.
                unique = {item.target.item_id: item for item in order[start:start + batch_size]}
                batch = list(unique.values())
                if len(batch) < 2:
                    continue
                vectors, actions, times = context_tensors(batch, device)
                positive, negative = model(vectors, actions, times, input_dim=dimension)
                query = positive if batch[0].head == "positive" else negative
                targets = torch.tensor([item.target.vector for item in batch], dtype=torch.float32, device=device)
                candidate_vectors = adapted_candidates(model, targets, dimension)
                logits = query @ candidate_vectors.T / 0.1
                loss = F.cross_entropy(logits, torch.arange(len(batch), device=device))
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite training objective")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                optimizer.step()
                steps[batch[0].head] += 1
                losses.append(float(loss.detach()))
        if not losses or not all(steps.values()):
            raise ValueError("Both heads need batches with at least two distinct target items")
        validation = evaluate_ranking(model, splits["validation"], device)
        history.append({"epoch": epoch + 1, "mean_loss": sum(losses) / len(losses), "validation": validation})
        if validation["ndcg_at_10"] > best_score:
            best_score = validation["ndcg_at_10"]
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state, strict=True)
    test_metrics = evaluate_ranking(model, splits["test"], device)
    sources = {session.source for session in sessions}
    test_sources = {session.source for session in sessions if subject_partition(session.subject_id) == "test"}
    training_source = next(iter(sources)) if len(sources) == 1 else "mixed"
    # Mixed synthetic/real evaluation is never mislabeled as real validation.
    evaluation_source = "real" if test_sources == {"real"} else "synthetic"
    manifest = BehaviorManifest(
        model_version=model_version, architecture=config.model_dump(), action_map=ACTION_MAP,
        embedding_sources=source_identity, training_source=training_source,
        training_examples=len(splits["train"]), dataset_sha256=file_sha256(dataset_path),
        evaluation_source=evaluation_source, evaluation_examples=int(test_metrics["evaluated_examples"]),
        split_strategy="user_disjoint_time_ordered", metrics=test_metrics, production_approved=False,
    )
    digest = save_behavior_checkpoint(output_path, model.eval(), manifest)
    report = {"model_version": model_version, "sha256": digest, "training_source": training_source,
              "evaluation_source": evaluation_source, "production_approved": False,
              "subject_counts": {key: len(value) for key, value in subjects.items()},
              "example_counts": {key: len(value) for key, value in splits.items()},
              "optimizer_steps": steps, "history": history, "test_metrics": test_metrics,
              "metric_scope": "Single next-positive-item ranking against distinct items in the held-out dataset snapshot, not the full production catalog."}
    Path(str(output_path) + ".metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
