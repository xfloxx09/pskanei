from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.scrape_settings import ScrapeSettings
from ..models.story import Story


async def get_daily_budget(db: AsyncSession) -> float:
    result = await db.execute(select(ScrapeSettings).where(ScrapeSettings.id == 1))
    settings = result.scalar_one_or_none()
    return settings.daily_budget if settings else 15.0


async def get_spent_today(db: AsyncSession) -> float:
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(Story).where(
            Story.updated_at >= today,
            Story.status.in_(["generating", "ready", "published"]),
        )
    )
    return float(len(result.scalars().all())) * 0.05  # placeholder: $0.05 per generated clip


async def check_budget(db: AsyncSession) -> bool:
    budget = await get_daily_budget(db)
    spent = await get_spent_today(db)
    return spent < budget
