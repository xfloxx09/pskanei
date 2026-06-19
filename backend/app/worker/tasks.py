import asyncio

from .celery_app import app


@app.task(bind=True, max_retries=3, default_retry_delay=120)
def scrape_and_score(self):
    try:
        asyncio.run(_run_scrape_pipeline())
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2, default_retry_delay=300)
def create_pipeline(self, story_id: str):
    try:
        asyncio.run(_run_create_pipeline(story_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _mark_failed_sync(story_id, str(exc))
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2, default_retry_delay=300)
def retry_failed_story(self, story_id: str):
    try:
        asyncio.run(_run_create_pipeline(story_id, skip_budget_check=True))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _mark_failed_sync(story_id, str(exc))
        raise self.retry(exc=exc)


def _mark_failed_sync(story_id: str, error: str):
    asyncio.run(_mark_failed(story_id, error))


async def _mark_failed(story_id: str, error: str):
    from uuid import UUID as _UUID

    from ..database import async_session
    from ..models.story import Story

    async with async_session() as db:
        story = await db.get(Story, _UUID(story_id))
        if story:
            story.status = "failed"
            story.content = story.content or {}
            story.content["error"] = error
            await db.commit()


# ---------------------------------------------------------------------------


async def _run_scrape_pipeline():
    import os

    os.environ.setdefault("ENVIRONMENT", "production")

    from sqlalchemy import select

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
            s
            for s in settings.sources
            if s.get("enabled") and s["id"] in SCRAPER_MAP
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
            merged_sources = raw.engagement.get(
                "merged_sources", [raw.url] if raw.url else []
            )

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


async def _run_create_pipeline(story_id: str, skip_budget_check: bool = False):
    import os

    os.environ.setdefault("ENVIRONMENT", "production")

    from sqlalchemy import select
    from uuid import UUID as _UUID

    from ..database import async_session
    from ..models.provider import Provider
    from ..models.story import Story
    from ..services.crypto import decrypt
    from ..services.budget import check_budget
    from ..services.providers import (
        DeepSeekProvider,
        ElevenLabsProvider,
        CreatomateProvider,
    )

    async with async_session() as db:
        story = await db.get(Story, _UUID(story_id))
        if not story:
            return {"status": "error", "reason": "story not found"}

        if story.status not in ("pending", "generating", "failed"):
            return {"status": "skipped", "reason": f"status is {story.status}"}

        if not skip_budget_check and not await check_budget(db):
            return {"status": "skipped", "reason": "daily budget exceeded"}

        story.status = "generating"
        story.content = story.content or {}
        story.content.pop("error", None)
        await db.commit()

        providers_result = await db.execute(
            select(Provider).where(Provider.enabled.is_(True))
        )
        all_providers = {p.id: p for p in providers_result.scalars().all()}

        def _get_key(provider_id: str) -> str:
            p = all_providers.get(provider_id)
            if p and p.api_key_encrypted:
                return decrypt(p.api_key_encrypted)
            return ""

        # --- Step 1: Generate prompt via DeepSeek ---
        llm = DeepSeekProvider(api_key=_get_key("p1"))
        prompt = await llm.generate_prompt(story.title, story.summary or "")
        story.content["prompt"] = prompt
        await db.commit()

        # --- Step 2: Generate TTS via ElevenLabs ---
        voiceover = prompt.get("voiceover_script", story.title)
        tts = ElevenLabsProvider(api_key=_get_key("p3"))
        tts_url = await tts.generate_speech(voiceover)
        story.content["tts_url"] = tts_url
        await db.commit()

        # --- Step 3: Render video via Creatomate ---
        video = CreatomateProvider(api_key=_get_key("p2"))
        video_url = await video.render_video(prompt, tts_url)
        story.content["video_url"] = video_url
        await db.commit()

        # --- Step 4: Finalize ---
        story.status = "ready"
        await db.commit()

        return {"status": "ok", "story_id": story_id, "video_url": video_url}
