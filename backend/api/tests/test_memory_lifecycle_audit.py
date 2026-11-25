from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_behavior_engine import BehaviorEngine,FinancialTier

@pytest.mark.asyncio
@pytest.mark.parametrize('owner',[True,0,-1,'7',7.0,2147483648])
async def test_price_history_owner_rejected_before_cache(owner):
    engine=object.__new__(BehaviorEngine);engine.cache=SimpleNamespace(client=SimpleNamespace(lrange=AsyncMock()))
    assert await engine._analyze_financial_dna(owner)==FinancialTier.MEDIUM
    engine.cache.client.lrange.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('values',[['nan'],['inf'],['-1'],['bad'],['1e308']*20])
async def test_corrupt_price_history_never_creates_spending_tier(values):
    engine=object.__new__(BehaviorEngine);engine.cache=SimpleNamespace(client=SimpleNamespace(lrange=AsyncMock(return_value=values)))
    assert await engine._analyze_financial_dna(7)==FinancialTier.MEDIUM
    engine.cache.client.lrange.assert_awaited_once_with(engine._key_price_hist(7),0,19)
