# backend/api/app/services/gamification_service.py

import logging
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.gamification import Badge, UserActivity, UserBadge

logger = logging.getLogger(__name__)

# Badge catalog: name -> (description, icon_url, points threshold on lifetime total)
BADGE_CATALOG = {
    "First Purchase": ("Completed your first airdeliver order.", "/images/badges/first_purchase.svg", 1),
    "Rising Collector": ("Earned 500 lifetime points.", "/images/badges/rising_collector.svg", 500),
    "Elite Curator": ("Earned 2,000 lifetime points.", "/images/badges/elite_curator.svg", 2000),
    "Titanium Patron": ("Earned 10,000 lifetime points.", "/images/badges/titanium_patron.svg", 10000),
}


class GamificationService:
    """Points and badges backed by the gamification models.

    Points: 1 point per whole currency unit of a paid order, recorded as a
    UserActivity row. Badges are awarded once per user when their lifetime
    points cross each catalog threshold.
    """

    async def award_points_for_purchase(
        self, db: AsyncSession, user_id: int, order_total: float
    ) -> int:
        points_to_award = int(order_total)
        if points_to_award <= 0:
            return 0

        db.add(
            UserActivity(
                user_id=user_id,
                activity_type="purchase",
                points_awarded=points_to_award,
            )
        )
        await db.commit()
        logger.info(
            "gamification points awarded",
            extra={"user_id": user_id, "points": points_to_award},
        )
        await self.check_and_award_badges(db, user_id)
        return points_to_award

    async def _lifetime_points(self, db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(UserActivity.points_awarded).where(UserActivity.user_id == user_id)
        )
        return sum(p for p in result.scalars().all() if p)

    async def _get_or_create_badge(
        self, db: AsyncSession, name: str, description: str, icon_url: str
    ) -> Badge:
        result = await db.execute(select(Badge).where(Badge.name == name))
        badge = result.scalars().first()
        if badge is None:
            badge = Badge(name=name, description=description, icon_url=icon_url)
            db.add(badge)
            await db.flush()
        return badge

    async def check_and_award_badges(self, db: AsyncSession, user_id: int) -> list[str]:
        lifetime_points = await self._lifetime_points(db, user_id)

        result = await db.execute(
            select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
        )
        owned_badge_ids = set(result.scalars().all())

        awarded: list[str] = []
        for name, (description, icon_url, threshold) in BADGE_CATALOG.items():
            if lifetime_points < threshold:
                continue
            badge = await self._get_or_create_badge(db, name, description, icon_url)
            if badge.id in owned_badge_ids:
                continue
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
            awarded.append(name)

        if awarded:
            await db.commit()
            logger.info(
                "gamification badges awarded",
                extra={"user_id": user_id, "badges": awarded},
            )
        return awarded


gamification_service = GamificationService()
