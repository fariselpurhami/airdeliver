"""Versioned artifact integrity, provenance and startup contracts."""
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import torch
from app.services.ai_behavior_engine import ACTION_MAP, BehaviorEngine, OmniNet, OmniNetConfig
from app.services.behavior_checkpoint import (
    BehaviorManifest, ModelArtifactError, load_behavior_checkpoint, save_behavior_checkpoint,
)


def tiny():
    return OmniNetConfig(internal_dim=24, intermediate_size=48, heads=4, layers=1,
                         dropout=0, supported_dims={"dim_24": 24})


def manifest(**changes):
    values = dict(model_version="test-v1", architecture=tiny().model_dump(), action_map=ACTION_MAP,
                  embedding_sources={"dim_24": "test-embedding@revision1"}, training_source="synthetic",
                  training_examples=12, dataset_sha256="a" * 64)
    values.update(changes)
    return BehaviorManifest(**values)


def test_checkpoint_roundtrip_has_identical_tensors_and_fingerprint(tmp_path):
    brain = OmniNet(tiny()).eval()
    path = tmp_path / "model.pt"
    digest = save_behavior_checkpoint(path, brain, manifest())
    loaded = load_behavior_checkpoint(path, expected_sha256=digest, expected_actions=ACTION_MAP,
                                     expected_embeddings={"dim_24": "test-embedding@revision1"})
    assert loaded.sha256 == digest
    assert loaded.manifest.training_source == "synthetic"
    assert all(torch.equal(value, loaded.state_dict[key]) for key, value in brain.state_dict().items())


def test_production_refuses_unpinned_or_unvalidated_artifact(tmp_path):
    path = tmp_path / "model.pt"
    digest = save_behavior_checkpoint(path, OmniNet(tiny()), manifest())
    with pytest.raises(ModelArtifactError, match="SHA256 pin"):
        load_behavior_checkpoint(path, production=True)
    with pytest.raises(ModelArtifactError, match="real-data"):
        load_behavior_checkpoint(path, production=True, expected_sha256=digest)


@pytest.mark.parametrize("change", ["hash", "actions", "embeddings"])
def test_incompatible_deployment_artifacts_are_rejected(tmp_path, change):
    path = tmp_path / "model.pt"
    save_behavior_checkpoint(path, OmniNet(tiny()), manifest())
    args = dict(expected_actions=ACTION_MAP, expected_embeddings={"dim_24": "test-embedding@revision1"})
    if change == "hash":
        args["expected_sha256"] = "0" * 64
    elif change == "actions":
        args["expected_actions"] = {"buy": 999}
    else:
        args["expected_embeddings"] = {"dim_24": "other-model@revision2"}
    with pytest.raises(ModelArtifactError):
        load_behavior_checkpoint(path, **args)


def test_nonfinite_save_does_not_replace_previous_good_checkpoint(tmp_path):
    path = tmp_path / "model.pt"
    brain = OmniNet(tiny())
    digest = save_behavior_checkpoint(path, brain, manifest())
    with torch.no_grad():
        next(brain.parameters()).fill_(float("nan"))
    with pytest.raises(ModelArtifactError, match="nonfinite"):
        save_behavior_checkpoint(path, brain, manifest())
    assert load_behavior_checkpoint(path).sha256 == digest


def test_synthetic_or_missing_real_metrics_cannot_be_marked_approved():
    with pytest.raises(ValueError, match="real-data"):
        manifest(production_approved=True)
    with pytest.raises(ValueError, match="baseline"):
        manifest(training_source="real", evaluation_source="real", evaluation_examples=4,
                 split_strategy="user_disjoint_time_ordered", production_approved=True,
                 metrics={"ndcg_at_10": 0.1, "mrr_at_10": 0.1, "baseline_ndcg_at_10": 0.5})


def test_engine_loads_checkpoint_instead_of_randomly_initializing_new_weights(tmp_path):
    path = tmp_path / "model.pt"
    brain = OmniNet(tiny()).eval()
    digest = save_behavior_checkpoint(path, brain, manifest())
    engine = BehaviorEngine(AsyncMock(), net_config=tiny(), checkpoint_path=str(path),
                            checkpoint_sha256=digest, embedding_sources={"dim_24": "test-embedding@revision1"})
    assert engine.model_status()["source"] == "synthetic"
    assert engine.model_status()["sha256"] == digest
    assert engine.model_status()["inference_ready"] is True
    assert all(torch.equal(value, engine.brain.state_dict()[key]) for key, value in brain.state_dict().items())


def test_no_checkpoint_never_exposes_random_inference_by_default():
    engine = BehaviorEngine(AsyncMock(), net_config=tiny())
    assert engine.brain is None
    assert engine.model_status()["inference_ready"] is False


@pytest.mark.asyncio
async def test_no_checkpoint_cannot_rerank_using_a_legacy_random_ghost():
    cache = AsyncMock()
    cache.get.return_value = '{"pos":[1],"neg":[0]}'
    engine = BehaviorEngine(cache, net_config=tiny())
    products = [{"id": 1, "vector": [1] * 24}, {"id": 2, "vector": [0] * 24}]
    assert await engine.collapse_wavefunction(7, products) == products
    cache.get.assert_not_awaited()


def test_untrained_artifact_cannot_be_relabelled_as_working_inference(tmp_path):
    path = tmp_path / "untrained.pt"
    save_behavior_checkpoint(path, OmniNet(tiny()), manifest(training_source="untrained", training_examples=0))
    with pytest.raises(ModelArtifactError, match="untrained checkpoint"):
        BehaviorEngine(AsyncMock(), net_config=tiny(), checkpoint_path=str(path), embedding_sources={"dim_24": "test-embedding@revision1"})


def test_ghosts_are_artifact_scoped_and_streams_are_embedding_scoped(tmp_path):
    path1, path2 = tmp_path / "one.pt", tmp_path / "two.pt"
    save_behavior_checkpoint(path1, OmniNet(tiny()), manifest())
    save_behavior_checkpoint(path2, OmniNet(tiny()), manifest(model_version="test-v2"))
    kwargs = dict(net_config=tiny(), embedding_sources={"dim_24": "test-embedding@revision1"})
    one = BehaviorEngine(AsyncMock(), checkpoint_path=str(path1), **kwargs)
    two = BehaviorEngine(AsyncMock(), checkpoint_path=str(path2), **kwargs)
    assert one.ghost_key(7) != two.ghost_key(7)
    assert one.stream_key(7, 24) == two.stream_key(7, 24)
    save_behavior_checkpoint(path2, OmniNet(tiny()), manifest(embedding_sources={"dim_24": "test-embedding@revision2"}))
    changed = BehaviorEngine(AsyncMock(), net_config=tiny(), checkpoint_path=str(path2), embedding_sources={"dim_24": "test-embedding@revision2"})
    assert changed.stream_key(7, 24) != one.stream_key(7, 24)


def test_production_without_artifact_does_not_construct_a_random_brain(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    import app.services.ai_behavior_engine as behavior
    settings = SimpleNamespace(APP_ENV="production", BEHAVIOR_CHECKPOINT_PATH=None, BEHAVIOR_CHECKPOINT_SHA256=None,
                               PRODUCT_TEXT_MODEL_REVISION=None, PRODUCT_VISION_MODEL_REVISION=None)
    monkeypatch.setattr(behavior, "get_core_settings", lambda: settings)
    constructor = Mock(side_effect=AssertionError("Random network construction is forbidden"))
    monkeypatch.setattr(behavior, "OmniNet", constructor)
    engine = behavior.BehaviorEngine(AsyncMock(), net_config=tiny())
    assert engine.model_status()["inference_ready"] is False
    constructor.assert_not_called()
    with pytest.raises(ModelArtifactError, match="development"):
        behavior.BehaviorEngine(AsyncMock(), net_config=tiny(), allow_untrained_inference=True)


@pytest.mark.asyncio
async def test_api_nlu_reuses_process_lifetime_behavior_engine():
    from types import SimpleNamespace
    from app.api.v1.endpoints.ai_ordering import get_ai_nlu_service
    shared = BehaviorEngine(AsyncMock(), net_config=tiny())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(behavior=shared)))
    kwargs = dict(request=request, db=object(), cache=AsyncMock(), rabbitmq=object(), commerce_engine=object(), llm_service=object())
    first = await get_ai_nlu_service(**kwargs)
    second = await get_ai_nlu_service(**kwargs)
    assert first.behavior_engine is shared is second.behavior_engine
