"""Versioned tensor-only behavior checkpoints with explicit data provenance.

Checkpoints are local deployment artifacts, never arbitrary user uploads.
Production callers must pin their SHA256 before loading them.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import torch
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelArtifactError(ValueError):
    pass


class BehaviorManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[1] = 1
    model_version: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    architecture: dict[str, Any]
    action_map: dict[str, int]
    embedding_sources: dict[str, str]
    training_source: Literal["untrained", "synthetic", "real", "mixed"]
    training_examples: int = Field(ge=0)
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    evaluation_source: Literal["none", "synthetic", "real"] = "none"
    evaluation_examples: int = Field(default=0, ge=0)
    split_strategy: Literal["none", "user_disjoint_time_ordered"] = "none"
    metrics: dict[str, float] = Field(default_factory=dict)
    production_approved: bool = False

    @field_validator("embedding_sources")
    @classmethod
    def sources_have_versions(cls, value):
        if not value or len(value) > 10:
            raise ValueError("One to ten embedding sources are required")
        for key, source in value.items():
            if not key.startswith("dim_") or not key[4:].isdigit() or int(key[4:]) <= 0:
                raise ValueError("Invalid embedding dimension")
            if "@" not in source or not all(source.rsplit("@", 1)) or len(source) > 256:
                raise ValueError("Embedding source must include its revision")
        return value

    @model_validator(mode="after")
    def provenance_is_consistent(self):
        if self.training_source != "untrained" and self.training_examples < 1:
            raise ValueError("Trained models need training examples")
        if self.evaluation_source == "none" and self.evaluation_examples:
            raise ValueError("Evaluation examples require provenance")
        if self.production_approved:
            required = {"ndcg_at_10", "mrr_at_10", "baseline_ndcg_at_10"}
            if (self.training_source not in {"real", "mixed"}
                    or self.evaluation_source != "real" or self.evaluation_examples < 1
                    or self.split_strategy != "user_disjoint_time_ordered"
                    or not required <= self.metrics.keys()):
                raise ValueError("Production approval requires held-out real-data evaluation")
            if any(not 0 <= self.metrics[key] <= 1 for key in required):
                raise ValueError("Ranking metrics must be within [0, 1]")
            if self.metrics["ndcg_at_10"] < self.metrics["baseline_ndcg_at_10"]:
                raise ValueError("Model did not meet its declared baseline")
        return self


@dataclass(frozen=True)
class LoadedBehaviorCheckpoint:
    manifest: BehaviorManifest
    state_dict: dict[str, torch.Tensor]
    sha256: str


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_tensor_state(state: Any) -> dict[str, torch.Tensor]:
    if not isinstance(state, dict) or not state:
        raise ModelArtifactError("Checkpoint has no tensor state")
    for name, tensor in state.items():
        if not isinstance(name, str) or not isinstance(tensor, torch.Tensor):
            raise ModelArtifactError("Checkpoint state must contain named tensors only")
        if tensor.layout != torch.strided or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all():
            raise ModelArtifactError("Checkpoint contains unsupported or nonfinite tensor values")
    return state


def save_behavior_checkpoint(path: str | Path, model: torch.nn.Module, manifest: BehaviorManifest) -> str:
    """Atomic replacement. A failed write leaves an earlier checkpoint intact."""
    manifest = BehaviorManifest.model_validate(manifest.model_dump())
    state = {key: value.detach().to("cpu").contiguous() for key, value in model.state_dict().items()}
    validate_tensor_state(state)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".behavior-", suffix=".pt", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save({"format_version": 1, "manifest": manifest.model_dump(mode="json"), "state_dict": state}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return file_sha256(target)


def load_behavior_checkpoint(
    path: str | Path, *, expected_sha256: str | None = None,
    expected_actions: dict[str, int] | None = None,
    expected_embeddings: dict[str, str] | None = None,
    production: bool = False,
) -> LoadedBehaviorCheckpoint:
    source = Path(path)
    if not source.is_file():
        raise ModelArtifactError("Checkpoint path must identify a regular local file")
    if production and not expected_sha256:
        raise ModelArtifactError("Production checkpoints require an explicit SHA256 pin")
    try:
        # Keep one file descriptor across hashing and deserialization so an
        # atomic deployment replacement cannot swap the verified artifact.
        with source.open("rb") as stream:
            if not 0 < os.fstat(stream.fileno()).st_size <= 2 * 1024 ** 3:
                raise ModelArtifactError("Checkpoint empty or larger than 2 GiB")
            hasher = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(block)
            digest = hasher.hexdigest()
            if expected_sha256 and digest != expected_sha256.lower():
                raise ModelArtifactError("Checkpoint SHA256 does not match deployment pin")
            stream.seek(0)
            packet = torch.load(stream, map_location="cpu", weights_only=True)
        if not isinstance(packet, dict) or packet.get("format_version") != 1:
            raise ModelArtifactError("Unsupported checkpoint format")
        manifest = BehaviorManifest.model_validate(packet.get("manifest"))
        state = validate_tensor_state(packet.get("state_dict"))
    except ModelArtifactError:
        raise
    except Exception as exc:
        raise ModelArtifactError("Invalid or unsafe behavior checkpoint") from exc
    if expected_actions is not None and manifest.action_map != expected_actions:
        raise ModelArtifactError("Checkpoint action vocabulary is incompatible")
    if expected_embeddings is not None and manifest.embedding_sources != expected_embeddings:
        raise ModelArtifactError("Checkpoint embedding sources are incompatible")
    if production and not manifest.production_approved:
        raise ModelArtifactError("Production requires an approved real-data evaluated checkpoint")
    return LoadedBehaviorCheckpoint(manifest=manifest, state_dict=state, sha256=digest)
