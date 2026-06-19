from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.scrape_settings import ScrapeSettings
from ..schemas.scrape_settings import ScrapeSettingsIn, ScrapeSettingsOut, SourceItem

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


def _default_sources() -> list[dict]:
    return [
        {"id": "gdelt", "name": "GDELT", "desc": "Global news index, updated every 15 min", "enabled": True},
        {"id": "reddit", "name": "Reddit", "desc": "r/all + r/popular, hot/top filtered by window", "enabled": True},
        {"id": "newsapi", "name": "NewsAPI", "desc": "Aggregated headlines across outlets", "enabled": True},
        {"id": "gtrends", "name": "Google Trends", "desc": "Realtime search interest by region", "enabled": False},
        {"id": "ytrending", "name": "YouTube trending", "desc": "YouTube Data API trending feed", "enabled": False},
    ]


async def _get_or_create_settings(db: AsyncSession) -> ScrapeSettings:
    result = await db.execute(select(ScrapeSettings).where(ScrapeSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = ScrapeSettings(
            id=1,
            time_window="6h",
            frequency_minutes=30,
            sources=_default_sources(),
        )
        db.add(settings)
        await db.flush()
    return settings


@router.get("/settings", response_model=ScrapeSettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    return ScrapeSettingsOut(
        window=settings.time_window,
        frequency=str(settings.frequency_minutes),
        sources=[SourceItem(**s) for s in settings.sources],
        updated_at=settings.updated_at,
    )


@router.post("/settings")
async def update_settings(body: ScrapeSettingsIn, db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    settings.time_window = body.window
    settings.frequency_minutes = int(body.frequency)
    settings.sources = [s.model_dump() for s in body.sources]
    settings.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


@router.post("/trigger")
async def trigger_scrape():
    # Try Celery first; if no Redis, run synchronously
    try:
        from ..worker.tasks import scrape_and_score
        result = scrape_and_score.delay()
        return {"success": True, "job_id": result.id, "mode": "celery"}
    except Exception as e:
        from ..worker.tasks import _run_scrape_pipeline
        data = await _run_scrape_pipeline()
        return {"success": True, "mode": "sync", "detail": data}
