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
    from ..services.crypto import decrypt
    from ..services.scrapers import (
        GDELTScraper,
        RedditScraper,
        NewsAPIScraper,
        GoogleTrendsScraper,
        YouTubeTrendingScraper,
    )
    from ..services.deduplicator import deduplicate
    from ..services.scorer import score_stories

    async with async_session() as db:
        result = await db.execute(
            select(ScrapeSettings).where(ScrapeSettings.id == 1)
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            return {"status": "skipped", "reason": "no settings"}

        scraper_keys = settings.scraper_keys or {}
        decrypted_keys = {}
        for k, v in scraper_keys.items():
            if v:
                try:
                    decrypted_keys[k] = decrypt(v)
                except Exception:
                    pass

        SCRAPER_MAP = {
            "gdelt": GDELTScraper(),
            "reddit": RedditScraper(),
            "newsapi": NewsAPIScraper(api_key=decrypted_keys.get("newsapi", "")),
            "gtrends": GoogleTrendsScraper(),
            "ytrending": YouTubeTrendingScraper(api_key=decrypted_keys.get("youtube", "")),
        }

        time_window = settings.time_window
        enabled_sources = [
            s
            for s in settings.sources
            if s.get("enabled") and s["id"] in SCRAPER_MAP
        ]

        if not enabled_sources:
            return {"status": "skipped", "reason": "no enabled sources"}

        all_raw = []
        source_errors = {}
        source_counts = {}
        for src_cfg in enabled_sources:
            scraper = SCRAPER_MAP[src_cfg["id"]]
            try:
                raw_stories = await scraper.fetch(time_window)
                source_counts[src_cfg["id"]] = len(raw_stories or [])
                all_raw.extend(raw_stories or [])
            except Exception as exc:
                source_errors[src_cfg["id"]] = str(exc)
                source_counts[src_cfg["id"]] = 0

        if not all_raw:
            return {
                "status": "skipped",
                "reason": "no stories fetched",
                "source_counts": source_counts,
                "source_errors": source_errors,
            }

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

        return {"status": "ok", "stories_saved": saved, "source_counts": source_counts, "source_errors": source_errors}


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


@app.task(bind=True, max_retries=2, default_retry_delay=120)
def publish_clip(self, clip_id: str):
    try:
        asyncio.run(_run_publish_clip(clip_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            _mark_clip_failed_sync(clip_id, str(exc))
        raise self.retry(exc=exc)


@app.task(name="app.worker.tasks.check_scheduled_posts")
def check_scheduled_posts():
    try:
        asyncio.run(_run_check_scheduled())
    except Exception as exc:
        print(f"[scheduler] check_scheduled_posts failed: {exc}")


def _mark_clip_failed_sync(clip_id: str, error: str):
    asyncio.run(_mark_clip_failed(clip_id, error))


async def _mark_clip_failed(clip_id: str, error: str):
    from uuid import UUID as _UUID

    from ..database import async_session
    from ..models.published_clip import PublishedClip

    async with async_session() as db:
        clip = await db.get(PublishedClip, _UUID(clip_id))
        if clip:
            clip.status = "failed"
            await db.commit()


async def _run_publish_clip(clip_id: str):
    import os

    os.environ.setdefault("ENVIRONMENT", "production")

    from datetime import datetime, timezone
    from uuid import UUID as _UUID

    from ..database import async_session
    from ..models.platform_account import PlatformAccount
    from ..models.published_clip import PublishedClip
    from ..models.story import Story
    from ..services.crypto import decrypt
    from ..services.storage import upload_to_r2
    from ..services.publishers import (
        YouTubePublisher,
        TikTokPublisher,
        InstagramPublisher,
        FacebookPublisher,
    )

    PUBLISHER_MAP = {
        "youtube": YouTubePublisher(),
        "tiktok": TikTokPublisher(),
        "instagram": InstagramPublisher(),
        "facebook": FacebookPublisher(),
    }

    async with async_session() as db:
        clip = await db.get(PublishedClip, _UUID(clip_id))
        if not clip:
            return {"status": "error", "reason": "clip not found"}

        story = await db.get(Story, clip.story_id)
        if not story:
            clip.status = "failed"
            await db.commit()
            return {"status": "error", "reason": "story not found"}

        platform = await db.get(PlatformAccount, clip.platform)
        if not platform or not platform.connected or not platform.enabled:
            clip.status = "failed"
            await db.commit()
            return {"status": "error", "reason": "platform not connected"}

        access_token = decrypt(platform.access_token_encrypted) if platform.access_token_encrypted else ""
        if not access_token:
            clip.status = "failed"
            await db.commit()
            return {"status": "error", "reason": "no access token"}

        publisher = PUBLISHER_MAP.get(clip.platform)
        if not publisher:
            clip.status = "failed"
            await db.commit()
            return {"status": "error", "reason": f"unknown platform {clip.platform}"}

        video_url = (story.content or {}).get("video_url", "")
        if not video_url:
            clip.status = "failed"
            await db.commit()
            return {"status": "error", "reason": "no video URL in story content"}

        r2_url = await upload_to_r2(video_url)

        prompt_data = (story.content or {}).get("prompt", {})
        caption = ""
        if isinstance(prompt_data, dict):
            caps = prompt_data.get("captions", {})
            platform_caps = caps.get(clip.platform, {})
            if isinstance(platform_caps, dict):
                hashtags = " ".join(platform_caps.get("hashtags", []))
                caption = f"{platform_caps.get('text', '')} {hashtags}".strip()

        try:
            result = await publisher.publish(
                video_url=r2_url or video_url,
                title=story.title,
                caption=caption or story.title,
                access_token=access_token,
            )
            clip.platform_post_id = result.get("post_id", "")
            clip.video_url = result.get("url", "")
            clip.status = "published"
            clip.published_at = datetime.now(timezone.utc)
            await db.commit()
            return {"status": "ok", "clip_id": clip_id, "post_id": result.get("post_id")}
        except Exception as exc:
            clip.status = "failed"
            await db.commit()
            raise


async def _run_check_scheduled():
    import os

    os.environ.setdefault("ENVIRONMENT", "production")

    from datetime import datetime, timezone
    from sqlalchemy import select

    from ..database import async_session
    from ..models.published_clip import PublishedClip

    async with async_session() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PublishedClip).where(
                PublishedClip.status == "scheduled",
                PublishedClip.scheduled_at <= now,
            )
        )
        due_clips = result.scalars().all()

        for clip in due_clips:
            clip.status = "publishing"
            await db.commit()
            publish_clip.delay(str(clip.id))

        return {"status": "ok", "due_clips": len(due_clips)}
