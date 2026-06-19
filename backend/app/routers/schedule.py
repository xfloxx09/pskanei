from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.published_clip import PublishedClip
from ..models.story import Story
from ..schemas.published_clip import PublishedClipOut, PublishRequest, ScheduleRequest

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("", response_model=list[PublishedClipOut])
async def list_schedule(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PublishedClip)
        .order_by(
            PublishedClip.scheduled_at.desc().nullslast(),
            PublishedClip.published_at.desc().nullslast(),
        )
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    clips = result.scalars().all()

    out = []
    for c in clips:
        title = ""
        story = await db.get(Story, c.story_id)
        if story:
            title = story.title

        when = ""
        if c.published_at:
            when = c.published_at.strftime("%b %d, %I:%M %p")
        elif c.scheduled_at:
            when = c.scheduled_at.strftime("%b %d, %I:%M %p")

        out.append(
            PublishedClipOut(
                id=c.id,
                title=title,
                platform=c.platform,
                status=c.status,
                when=when,
                scheduled_at=c.scheduled_at,
                published_at=c.published_at,
            )
        )
    return out


@router.post("")
async def publish_now(body: PublishRequest, db: AsyncSession = Depends(get_db)):
    ready_story = await db.execute(
        select(Story)
        .where(Story.status == "ready")
        .order_by(Story.score.desc())
        .limit(1)
    )
    story = ready_story.scalar_one_or_none()
    if not story:
        raise HTTPException(404, "No ready stories found")

    if not body.platforms:
        raise HTTPException(400, "No platforms specified")

    from ..worker.tasks import publish_clip

    for platform_id in body.platforms:
        clip = PublishedClip(
            story_id=story.id,
            platform=platform_id,
            status="publishing",
            scheduled_at=datetime.now(timezone.utc),
        )
        db.add(clip)
        await db.flush()
        try:
            publish_clip.delay(str(clip.id))
        except Exception:
            from ..worker.tasks import _run_publish_clip
            import asyncio
            asyncio.create_task(_run_publish_clip(str(clip.id)))

    await db.commit()

    return {"success": True, "story_id": str(story.id), "platforms": body.platforms}


@router.post("/{story_id}/publish")
async def publish_story(
    story_id: UUID,
    body: PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    if story.status != "ready":
        raise HTTPException(409, "Story is not ready")

    if not body.platforms:
        raise HTTPException(400, "No platforms specified")

    from ..worker.tasks import publish_clip

    for platform_id in body.platforms:
        clip = PublishedClip(
            story_id=story.id,
            platform=platform_id,
            status="publishing",
            scheduled_at=datetime.now(timezone.utc),
        )
        db.add(clip)
        await db.flush()
        try:
            publish_clip.delay(str(clip.id))
        except Exception:
            from ..worker.tasks import _run_publish_clip
            import asyncio
            asyncio.create_task(_run_publish_clip(str(clip.id)))

    story.status = "published"
    await db.commit()

    return {"success": True, "publishing_to": body.platforms}


@router.post("/{story_id}/schedule")
async def schedule_story(
    story_id: UUID,
    body: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    if story.status != "ready":
        raise HTTPException(409, "Story is not ready")

    if not body.platforms:
        raise HTTPException(400, "No platforms specified")

    for platform_id in body.platforms:
        db.add(
            PublishedClip(
                story_id=story.id,
                platform=platform_id,
                status="scheduled",
                scheduled_at=body.scheduled_at,
            )
        )

    await db.commit()

    return {"success": True, "scheduled_for": str(body.scheduled_at), "platforms": body.platforms}
