from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.platform_account import PlatformAccount
from ..services.crypto import encrypt

router = APIRouter(prefix="/api/auth", tags=["auth"])

from ..routers.platforms import _oauth_states

FRONTEND_URL = "http://localhost:3000"


@router.get("/{platform_id}/callback")
async def oauth_callback(
    platform_id: str,
    code: str = Query(...),
    state: str = Query(None),
    error: str | None = Query(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}?auth_error={error}")

    expected_platform = _oauth_states.pop(state, None) if state else None
    if expected_platform and expected_platform != platform_id:
        return RedirectResponse(f"{FRONTEND_URL}?auth_error=state_mismatch")

    platform = await db.get(PlatformAccount, platform_id)
    if not platform:
        return RedirectResponse(f"{FRONTEND_URL}?auth_error=platform_not_found")

    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/auth/{platform_id}/callback"

    try:
        if platform_id == "youtube":
            async with httpx.AsyncClient(timeout=30) as http:
                resp = await http.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.youtube_client_id,
                        "client_secret": settings.youtube_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            platform.access_token_encrypted = encrypt(data["access_token"])
            platform.refresh_token_encrypted = encrypt(data.get("refresh_token", "")) if data.get("refresh_token") else None
            platform.token_expires_at = datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600)
            platform.token_expires_at = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600),
                tz=timezone.utc,
            )
            platform.platform_user_id = data.get("sub", "")

        elif platform_id == "tiktok":
            if not settings.tiktok_client_secret:
                raise ValueError("TikTok client secret not configured")

            async with httpx.AsyncClient(timeout=30) as http:
                resp = await http.post(
                    "https://open.tiktokapis.com/v2/oauth/token/",
                    data={
                        "client_key": settings.tiktok_client_id,
                        "client_secret": settings.tiktok_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            platform.access_token_encrypted = encrypt(data["access_token"])
            platform.refresh_token_encrypted = encrypt(data.get("refresh_token", "")) if data.get("refresh_token") else None
            platform.token_expires_at = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + data.get("expires_in", 86400),
                tz=timezone.utc,
            )

        elif platform_id in ("instagram", "facebook"):
            client_id = settings.instagram_client_id if platform_id == "instagram" else settings.facebook_client_id
            client_secret = settings.instagram_client_secret if platform_id == "instagram" else settings.facebook_client_secret

            async with httpx.AsyncClient(timeout=30) as http:
                resp = await http.get(
                    "https://graph.facebook.com/v21.0/oauth/access_token",
                    params={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            short_token = data["access_token"]

            long_resp = await http.get(
                "https://graph.facebook.com/v21.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "fb_exchange_token": short_token,
                },
            )
            long_resp.raise_for_status()
            long_data = long_resp.json()

            platform.access_token_encrypted = encrypt(long_data["access_token"])
            platform.token_expires_at = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + long_data.get("expires_in", 5184000),
                tz=timezone.utc,
            )

        else:
            return RedirectResponse(f"{FRONTEND_URL}?auth_error=unknown_platform")

        platform.connected = True
        await db.commit()

        return RedirectResponse(f"{FRONTEND_URL}?auth_success={platform_id}")

    except Exception as exc:
        return RedirectResponse(f"{FRONTEND_URL}?auth_error={str(exc)}")
