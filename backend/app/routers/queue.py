from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.story import Story
from ..schemas.story import StoryOut

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("", response_model=list[StoryOut])
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
    return [StoryOut.model_validate(s) for s in stories]


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
    if not _has_key("p1"):
        missing.append("DeepSeek (prompt generation)")
    if not _has_key("p3"):
        missing.append("ElevenLabs (voiceover)")
    if not _has_key("p2"):
        missing.append("Creatomate (video assembly)")

    if missing:
        raise HTTPException(400, f"Missing API keys: {', '.join(missing)}. Set them in AI Providers tab.")

    story.status = "generating"
    await db.commit()
    await db.refresh(story)

    from ..worker.tasks import _run_create_pipeline
    import asyncio
    asyncio.create_task(_run_create_pipeline(str(story_id)))

    return {"success": True, "story": StoryOut.model_validate(story)}


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
    return {"success": True, "story": StoryOut.model_validate(story)}


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

    return {"success": True, "story": StoryOut.model_validate(story)}
