from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.story import Story
from ..models.scrape_settings import ScrapeSettings
from ..schemas.story import StoryOut, StoryDetail


def _enrich_story_out(story: Story, out: StoryOut):
    c = story.content or {}
    if isinstance(c, dict):
        if "ai_curation" in c and c["ai_curation"]:
            out.ai_curation = c["ai_curation"]
        elif out.status == "pending":
            out.status_msg = "Not analyzed"
        if "status_msg" in c and c["status_msg"]:
            out.status_msg = c["status_msg"]
        elif "error" in c and c["error"]:
            out.status_msg = c["error"][:80]
        elif story.status == "failed":
            out.status_msg = "Unknown error"


router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("")
async def list_stories(
    window: str | None = Query(None, description="Time window filter"),
    status: str | None = Query(None, description="Status filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Story).order_by(Story.score.desc(), Story.spotted_at.desc())
    if window:
        stmt = stmt.where(Story.time_window == window)
    if status:
        stmt = stmt.where(Story.status == status)
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    stories = result.scalars().all()
    out = []
    for s in stories:
        await db.refresh(s)  # Force fresh data
        item = StoryOut.model_validate(s)
        _enrich_story_out(s, item)
        out.append(item.model_dump())
    return out


@router.post("/{story_id}/approve")
async def approve_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(404, "Story not found")
    if story.status != "pending":
        raise HTTPException(409, f"Story is not pending (currently {story.status})")

    from ..models.provider import Provider
    from ..services.crypto import decrypt
    providers_result = await db.execute(
        select(Provider).where(Provider.enabled.is_(True))
    )
    all_providers = {p.id: p for p in providers_result.scalars().all()}

    def _has_key(pid: str) -> bool:
        p = all_providers.get(pid)
        if not p or not p.api_key_encrypted:
            return False
        try:
            return bool(decrypt(p.api_key_encrypted))
        except Exception:
            return False

    missing = []
    # Check by role, not by hardcoded ID — works with custom providers too
    llm_providers = [p for p in all_providers.values() if p.role and "prompt" in p.role.lower()]
    tts_providers = [p for p in all_providers.values() if p.role and ("tts" in p.role.lower() or "voiceover" in p.role.lower())]
    video_providers = [p for p in all_providers.values() if p.role and ("video" in p.role.lower() or "avatar" in p.role.lower())]

    has_llm = any(_has_key(p.id) for p in llm_providers)
    has_video = any(_has_key(p.id) for p in video_providers)

    if not has_llm:
        names = [p.name for p in llm_providers]
        if names:
            missing.append(f"LLM (enabled but no key: {', '.join(names)})")
        else:
            missing.append("LLM (no providers enabled. Add one via Add Provider dropdown)")

    if not has_video:
        names = [p.name for p in video_providers]
        if names:
            missing.append(f"Video (enabled but no key: {', '.join(names)})")
        else:
            missing.append("Video (no providers enabled. Add one via Add Provider dropdown)")

    if missing:
        raise HTTPException(400, f"Missing API keys: {', '.join(missing)}. Set them in AI Providers tab.")

    story.status = "generating"
    await db.commit()
    await db.refresh(story)

    from ..worker.tasks import _run_create_pipeline
    import asyncio
    asyncio.create_task(_run_create_pipeline(str(story_id)))

    out = StoryOut.model_validate(story)
    _enrich_story_out(story, out)
    return {"success": True, "story": out}


@router.post("/{story_id}/reject")
async def reject_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(404, "Story not found")
    if story.status != "pending":
        raise HTTPException(409, f"Story is not pending (currently {story.status})")
    story.status = "rejected"
    await db.commit()
    await db.refresh(story)
    out = StoryOut.model_validate(story)
    _enrich_story_out(story, out)
    return {"success": True, "story": out}


@router.post("/{story_id}/cancel")
async def cancel_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    if story.status != "generating":
        raise HTTPException(409, "Story is not generating")
    story.status = "failed"
    story.content = story.content or {}
    story.content["status_msg"] = "Cancelled"
    story.content["error"] = "User cancelled"
    story.content["cancelled"] = True
    await db.commit()
    return {"success": True}


@router.post("/{story_id}/retry")
async def retry_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(404, "Story not found")
    if story.status not in ("failed", "generating"):
        raise HTTPException(409, f"Story is not retryable (currently {story.status})")

    from ..worker.tasks import retry_failed_story

    story.status = "generating"
    story.content = story.content or {}
    story.content.pop("error", None)
    await db.commit()

    from ..worker.tasks import _run_create_pipeline
    import asyncio
    asyncio.create_task(_run_create_pipeline(str(story_id), skip_budget_check=True))

    out = StoryOut.model_validate(story)
    _enrich_story_out(story, out)
    return {"success": True, "story": out}


@router.get("/debug/{story_id}/raw")
async def debug_raw_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    return {
        "id": str(story.id),
        "status": story.status,
        "content": story.content,
    }


@router.get("/{story_id}")
async def get_story(story_id: UUID, db: AsyncSession = Depends(get_db)):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    data = StoryDetail.model_validate(story)
    data.content = story.content
    _enrich_story_out(story, data)
    return data


@router.delete("")
async def clear_queue(
    status: str | None = Query(None, description="Only delete stories with this status"),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete
    stmt = delete(Story)
    if status:
        stmt = stmt.where(Story.status == status)
    result = await db.execute(stmt)
    await db.commit()
    return {"deleted": result.rowcount}


@router.post("/curate")
async def curate_queue(db: AsyncSession = Depends(get_db)):
    from ..models.provider import Provider
    from ..services.crypto import decrypt
    from ..services.curator import curate_stories

    provider_row = await db.get(Provider, "p1")
    deepseek_key = ""
    if provider_row and provider_row.enabled and provider_row.api_key_encrypted:
        try:
            deepseek_key = decrypt(provider_row.api_key_encrypted)
        except Exception:
            pass

    if not deepseek_key:
        raise HTTPException(400, "DeepSeek API key not configured in AI Providers tab")

    result = await db.execute(
        select(Story)
        .order_by(Story.score.desc())
        .limit(100)
    )
    stories = result.scalars().all()

    if not stories:
        raise HTTPException(404, "No stories in queue")

    batch = [
        {"id": str(s.id), "title": s.title, "score": s.score, "source": s.source, "content": (s.content or {}).get("article_text", "")}
        for s in stories
    ]

    all_analyses = {}

    custom_prompt = ""
    s_result = await db.execute(select(ScrapeSettings).where(ScrapeSettings.id == 1))
    s_obj = s_result.scalar_one_or_none()
    if s_obj and s_obj.prompt_templates:
        custom_prompt = s_obj.prompt_templates.get("curator", "")

    for i in range(0, len(batch), 10):
        chunk = batch[i:i + 10]
        try:
            curation = await curate_stories(chunk, deepseek_key, custom_prompt=custom_prompt)
            for a in curation.get("analyses", []):
                all_analyses[a["id"]] = a
        except Exception as e:
            raise HTTPException(502, f"DeepSeek API error on batch {i//10 + 1}: {str(e)}")

    # Retry individually for missed stories
    missing = [s for s in batch if s["id"] not in all_analyses]
    for s in missing:
        try:
            curation = await curate_stories([s], deepseek_key, custom_prompt=custom_prompt)
            for a in curation.get("analyses", []):
                all_analyses[a["id"]] = a
        except Exception:
            pass

    # Pick top 3 by AI viral_score
    sorted_all = sorted(all_analyses.values(), key=lambda a: a.get("viral_score", 0), reverse=True)
    top_ids = set(a["id"] for a in sorted_all[:3])
    for a in sorted_all[:3]:
        a["is_top_pick"] = True
    for a in sorted_all[3:]:
        a["is_top_pick"] = False
    updated = 0

    for sid, analysis in all_analyses.items():
        try:
            s = await db.get(Story, UUID(sid))
            if s:
                s.content = s.content or {}
                s.content["ai_curation"] = {
                    "category": analysis.get("category", ""),
                    "viral_score": analysis.get("viral_score", 0),
                    "hook_angle": analysis.get("hook_angle", ""),
                    "reasoning": analysis.get("reasoning", ""),
                    "is_top_pick": sid in top_ids,
                }
                updated += 1
        except (ValueError, TypeError):
            pass

    await db.commit()
    return {"success": True, "analyzed": updated, "top_pick_ids": list(top_ids)}


@router.patch("/{story_id}/prompt")
async def save_prompt(story_id: UUID, body: dict, db: AsyncSession = Depends(get_db)):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    story.content = story.content or {}
    story.content["prompt"] = {
        **story.content.get("prompt", {}),
        **body,
    }
    await db.commit()
    return {"success": True}


@router.post("/{story_id}/generate-video")
async def generate_video(story_id: UUID, db: AsyncSession = Depends(get_db)):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    if not (story.content or {}).get("prompt"):
        raise HTTPException(400, "No prompt to render. Run generation first.")

    from ..worker.tasks import _run_create_pipeline
    import asyncio

    story.status = "generating"
    story.content["status_msg"] = "Starting video render..."
    story.content.pop("error", None)
    await db.commit()

    asyncio.create_task(_run_create_pipeline(str(story_id), skip_prompt=True))

    return {"success": True}
