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
