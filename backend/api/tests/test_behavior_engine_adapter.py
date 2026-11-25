"""Adapter-seam tests for BehaviorEngine public facades."""
from unittest.mock import AsyncMock

import pytest

@pytest.mark.asyncio
async def test_analyze_financial_dna_public_alias_matches_private():
    """The NLU pipeline calls analyze_financial_dna via hasattr guard; the
    public alias must exist and delegate to the private implementation."""
    from app.services.ai_behavior_engine import BehaviorEngine
    assert hasattr(BehaviorEngine, "analyze_financial_dna")

    cache = AsyncMock()
    engine = BehaviorEngine(cache)
    engine._analyze_financial_dna = AsyncMock(return_value="HIGH")
    result = await engine.analyze_financial_dna(7)
    engine._analyze_financial_dna.assert_awaited_once_with(7)
    assert result == "HIGH"


@pytest.fixture(autouse=True)
def reduced_test_brain(monkeypatch):
    """Test adapters with real tensors without allocating the production brain."""
    import app.services.ai_behavior_engine as module
    config = module.OmniNetConfig(internal_dim=24, intermediate_size=48, heads=4,
                                 layers=1, supported_dims={"dim_1536": 1536})
    monkeypatch.setattr(module, "OmniNetConfig", lambda: config)
