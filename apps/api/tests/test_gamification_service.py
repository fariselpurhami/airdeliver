"""Gamification service: points persistence and badge threshold logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.gamification_service import GamificationService


@pytest.mark.asyncio
async def test_award_points_persists_activity_and_commits():
    svc = GamificationService()
    db = AsyncMock()
    with patch.object(svc, "check_and_award_badges", new=AsyncMock(return_value=[])):
        pts = await svc.award_points_for_purchase(db, user_id=5, order_total=42.9)
    assert pts == 42
    db.add.assert_called_once()
    activity = db.add.call_args.args[0]
    assert activity.user_id == 5
    assert activity.activity_type == "purchase"
    assert activity.points_awarded == 42
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_zero_total_awards_nothing():
    svc = GamificationService()
    db = AsyncMock()
    pts = await svc.award_points_for_purchase(db, user_id=5, order_total=0)
    assert pts == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_badges_awarded_only_past_threshold_and_once():
    svc = GamificationService()
    db = AsyncMock()

    # lifetime 600 -> First Purchase + Rising Collector, not the higher tiers
    lifetime = MagicMock()
    lifetime.scalars.return_value.all.return_value = [600]
    owned = MagicMock()
    owned.scalars.return_value.all.return_value = []
    badge_lookup = MagicMock()
    badge_lookup.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(side_effect=[lifetime, owned, badge_lookup, badge_lookup])
    db.flush = AsyncMock()

    awarded = await svc.check_and_award_badges(db, user_id=5)
    assert set(awarded) == {"First Purchase", "Rising Collector"}
    assert db.add.call_count == 4  # 2 badge rows + 2 user_badge rows
