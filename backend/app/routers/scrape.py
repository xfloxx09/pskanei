from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.scrape_settings import ScrapeSettings
from ..schemas.scrape_settings import ScrapeSettingsIn, ScrapeSettingsOut, SourceItem
from ..services.crypto import encrypt, decrypt, mask_key

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


def _masked_keys(encrypted_keys: dict) -> dict[str, str]:
    out = {}
    for k, v in encrypted_keys.items():
        if v:
            try:
                decrypted = decrypt(v)
                out[k] = mask_key(decrypted)
            except Exception:
                out[k] = ""
        else:
            out[k] = ""
    return out


@router.get("/settings", response_model=ScrapeSettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    return ScrapeSettingsOut(
        window=settings.time_window,
        frequency=str(settings.frequency_minutes),
        sources=[SourceItem(**s) for s in settings.sources],
        scraper_keys=_masked_keys(settings.scraper_keys or {}),
        updated_at=settings.updated_at,
    )


@router.post("/settings")
async def update_settings(body: ScrapeSettingsIn, db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    settings.time_window = body.window
    settings.frequency_minutes = int(body.frequency)
    settings.sources = [s.model_dump() for s in body.sources]

    new_keys = {}
    for k, v in body.scraper_keys.items():
        if v and not v.startswith("****"):
            new_keys[k] = encrypt(v)
        elif k in (settings.scraper_keys or {}):
            new_keys[k] = settings.scraper_keys[k]
    settings.scraper_keys = new_keys

    settings.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


@router.get("/prompts")
async def get_prompts(db: AsyncSession = Depends(get_db)):
    from ..schemas.scrape_settings import DEFAULT_PROMPT_TEMPLATES
    settings = await _get_or_create_settings(db)
    prompts = dict(DEFAULT_PROMPT_TEMPLATES)
    stored = settings.prompt_templates or {}
    if isinstance(stored, dict):
        prompts.update(stored)
    return {"prompts": prompts}


@router.post("/prompts")
async def save_prompts(body: dict, db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    if "prompts" in body:
        settings.prompt_templates = body["prompts"]
    settings.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"success": True}


@router.get("/debug/scrape/{source_id}")
async def debug_scrape(source_id: str):
    from ..services.scrapers import (
        GDELTScraper,
        RedditScraper,
        NewsAPIScraper,
        YouTubeTrendingScraper,
    )
    scrapers = {
        "gdelt": GDELTScraper,
        "reddit": RedditScraper,
        "newsapi": NewsAPIScraper,
        "ytrending": YouTubeTrendingScraper,
    }
    cls = scrapers.get(source_id)
    if not cls:
        return {"error": f"unknown source: {source_id}"}

    try:
        scraper = cls()
        stories = await scraper.fetch("6h")
        return {
            "source": source_id,
            "count": len(stories),
            "titles": [s.title[:80] for s in stories[:5]],
        }
    except Exception as e:
        return {"source": source_id, "error": str(e)}


@router.post("/trigger")
async def trigger_scrape():
    from ..worker.tasks import _run_scrape_pipeline
    try:
        data = await _run_scrape_pipeline()
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "detail": data, "mode": "sync"}
