import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.platform_account import PlatformAccount
from ..schemas.platform_account import PlatformAccountOut, PlatformSaveRequest
from ..services.crypto import decrypt, encrypt

router = APIRouter(prefix="/api/platforms", tags=["platforms"])

PLATFORM_DEFAULTS = [
    {"id": "youtube", "name": "YouTube Shorts", "connected": False, "daily_cap": 6, "enabled": True},
    {"id": "tiktok", "name": "TikTok", "connected": False, "daily_cap": 15, "enabled": True},
    {"id": "instagram", "name": "Instagram Reels", "connected": False, "daily_cap": 10, "enabled": True},
    {"id": "facebook", "name": "Facebook Reels", "connected": False, "daily_cap": 10, "enabled": True},
]

_oauth_states: dict[str, str] = {}


async def _ensure_defaults(db: AsyncSession):
    for pd in PLATFORM_DEFAULTS:
        existing = await db.get(PlatformAccount, pd["id"])
        if not existing:
            db.add(PlatformAccount(**pd))
    await db.flush()


@router.get("", response_model=list[PlatformAccountOut])
async def list_platforms(db: AsyncSession = Depends(get_db)):
    await _ensure_defaults(db)
    result = await db.execute(select(PlatformAccount))
    platforms = result.scalars().all()
    return [
        PlatformAccountOut(
            id=p.id,
            name=p.name,
            connected=p.connected,
            dailyCap=p.daily_cap,
            enabled=p.enabled,
        )
        for p in platforms
    ]


@router.post("")
async def save_platforms(body: PlatformSaveRequest, db: AsyncSession = Depends(get_db)):
    await _ensure_defaults(db)
    for item in body.platforms:
        p = await db.get(PlatformAccount, item.id)
        if p:
            p.daily_cap = item.dailyCap
            p.enabled = item.enabled
    await db.commit()
    return {"success": True}


@router.get("/{platform_id}/connect")
async def connect_platform(platform_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _ensure_defaults(db)
    platform = await db.get(PlatformAccount, platform_id)
    if not platform:
        raise HTTPException(404, "Platform not found")

    base_url = str(request.base_url).rstrip("/")
    callback_url = f"{base_url}/api/auth/{platform_id}/callback"
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = platform_id

    if platform_id == "youtube":
        if not settings.youtube_client_id:
            raise HTTPException(400, "YouTube OAuth not configured")
        params = {
            "client_id": settings.youtube_client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    elif platform_id == "tiktok":
        params = {
            "client_key": settings.tiktok_client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "video.publish",
            "state": state,
        }
        url = f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"

    elif platform_id in ("instagram", "facebook"):
        client_id = settings.instagram_client_id if platform_id == "instagram" else settings.facebook_client_id
        if not client_id:
            raise HTTPException(400, f"{platform_id} OAuth not configured")

        scope = "pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish" if platform_id == "instagram" else "pages_manage_posts,pages_read_engagement"
        params = {
            "client_id": client_id,
            "redirect_uri": callback_url,
            "scope": scope,
            "state": state,
        }
        url = f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}"

    else:
        raise HTTPException(400, f"Unknown platform: {platform_id}")

    return RedirectResponse(url)


@router.delete("/{platform_id}/token")
async def disconnect_platform(platform_id: str, db: AsyncSession = Depends(get_db)):
    platform = await db.get(PlatformAccount, platform_id)
    if not platform:
        raise HTTPException(404, "Platform not found")
    platform.connected = False
    platform.access_token_encrypted = None
    platform.refresh_token_encrypted = None
    platform.token_expires_at = None
    platform.platform_user_id = None
    await db.commit()
    return {"success": True}
