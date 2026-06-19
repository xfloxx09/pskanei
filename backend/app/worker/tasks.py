import asyncio

from .celery_app import app


@app.task(bind=True, max_retries=3, default_retry_delay=120)
def scrape_and_score(self):
    try:
        asyncio.run(_run_pipeline())
    except Exception as exc:
        raise self.retry(exc=exc)


async def _run_pipeline():
    import os

    os.environ.setdefault("ENVIRONMENT", "production")

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from ..database import async_session
    from ..models.scrape_settings import ScrapeSettings
    from ..models.story import Story
    from ..services.scrapers import (
        GDELTScraper,
        RedditScraper,
        NewsAPIScraper,
        GoogleTrendsScraper,
        YouTubeTrendingScraper,
    )
    from ..services.deduplicator import deduplicate
    from ..services.scorer import score_stories

    SCRAPER_MAP = {
        "gdelt": GDELTScraper(),
        "reddit": RedditScraper(),
        "newsapi": NewsAPIScraper(),
        "gtrends": GoogleTrendsScraper(),
        "ytrending": YouTubeTrendingScraper(),
    }

    async with async_session() as db:
        result = await db.execute(
            select(ScrapeSettings).where(ScrapeSettings.id == 1)
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            return {"status": "skipped", "reason": "no settings"}

        time_window = settings.time_window
        enabled_sources = [
            s for s in settings.sources if s.get("enabled") and s["id"] in SCRAPER_MAP
        ]

        if not enabled_sources:
            return {"status": "skipped", "reason": "no enabled sources"}

        all_raw = []
        for src_cfg in enabled_sources:
            scraper = SCRAPER_MAP[src_cfg["id"]]
            try:
                raw_stories = await scraper.fetch(time_window)
                all_raw.extend(raw_stories)
            except Exception as exc:
                print(f"[scraper] {src_cfg['id']} failed: {exc}")

        if not all_raw:
            return {"status": "skipped", "reason": "no stories fetched"}

        unique = deduplicate(all_raw)
        scored = score_stories(unique, time_window)

        saved = 0
        for raw in scored:
            breakdown = raw.engagement.get("_score_breakdown", {})
            score_val = breakdown.get("composite", 0)
            merged_sources = raw.engagement.get("merged_sources", [raw.url] if raw.url else [])
            merged_count = raw.engagement.get("merged_count", 1)
            engagement_out = {k: v for k, v in raw.engagement.items() if not k.startswith("_")}

            new_story = Story(
                title=raw.title,
                url=raw.url,
                source=raw.source,
                source_urls=merged_sources,
                summary=raw.summary or "",
                score=score_val,
                score_breakdown=breakdown,
                time_window=time_window,
                status="pending",
            )
            db.add(new_story)
            saved += 1

        await db.commit()

        return {"status": "ok", "stories_saved": saved}
