"""Characterize price-history tier sensitivity, not approval to infer wealth.

Only synthetic observations; no model allocation or provider call.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_behavior_engine import BehaviorEngine

@pytest.mark.asyncio
@pytest.mark.parametrize('history,expected',[
 ([], 'MEDIUM'),(['100']*20,'LOW'),(['1000']*20,'HIGH'),
 (['100']*19+['15000'],'HIGH'),(['nan'],'MEDIUM'),(['-1'],'MEDIUM'),
])
async def test_actual_history_classifier_is_fixed_scale_average_not_explicit_budget(history,expected):
 engine=object.__new__(BehaviorEngine)
 read=AsyncMock(return_value=history)
 engine.cache=SimpleNamespace(client=SimpleNamespace(lrange=read))
 assert await engine.analyze_financial_dna(7)==expected
 read.assert_awaited_once_with(engine._key_price_hist(7),0,19)

@pytest.mark.asyncio
async def test_same_history_shape_scaled_numerically_changes_tier_without_goal_change():
 engine=object.__new__(BehaviorEngine)
 reader=AsyncMock(side_effect=[['100']*20,['1000']*20])
 engine.cache=SimpleNamespace(client=SimpleNamespace(lrange=reader))
 # Synthetic scale contrast, not an asserted currency conversion. There is no
 # denomination, market or current-budget parameter at this method boundary.
 assert await engine.analyze_financial_dna(7)=='LOW'
 assert await engine.analyze_financial_dna(7)=='HIGH'
