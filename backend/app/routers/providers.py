from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.provider import Provider
from ..models.scrape_settings import ScrapeSettings
from ..schemas.provider import ProvidersResponse, ProvidersSaveRequest, ProviderItemOut
from ..services.crypto import decrypt, encrypt, mask_key

router = APIRouter(prefix="/api/providers", tags=["providers"])


async def _get_or_create_settings(db: AsyncSession) -> ScrapeSettings:
    result = await db.execute(select(ScrapeSettings).where(ScrapeSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = ScrapeSettings(id=1, daily_budget=15.0)
        db.add(settings)
        await db.flush()
    return settings


@router.get("", response_model=ProvidersResponse)
async def get_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Provider))
    providers = result.scalars().all()
    settings = await _get_or_create_settings(db)

    provider_outs = []
    for p in providers:
        decrypted = decrypt(p.api_key_encrypted) if p.api_key_encrypted else ""
        provider_outs.append(
            ProviderItemOut(
                id=p.id,
                name=p.name,
                role=p.role,
                apiKey=mask_key(decrypted),
                endpoint=p.endpoint or "",
                enabled=p.enabled,
            )
        )

    return ProvidersResponse(
        providers=provider_outs,
        daily_budget=settings.daily_budget,
    )


@router.post("")
async def save_providers(body: ProvidersSaveRequest, db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    settings.daily_budget = body.daily_budget
    settings.updated_at = datetime.now(timezone.utc)

    incoming_ids = {p.id for p in body.providers}

    existing = await db.execute(select(Provider))
    for p in existing.scalars().all():
        if p.id not in incoming_ids:
            await db.delete(p)

    for item in body.providers:
        existing_p = await db.get(Provider, item.id)
        encrypted = encrypt(item.apiKey) if item.apiKey and not item.apiKey.startswith("****") else None

        if existing_p:
            existing_p.name = item.name
            existing_p.role = item.role
            existing_p.endpoint = item.endpoint or None
            existing_p.enabled = item.enabled
            if encrypted is not None:
                existing_p.api_key_encrypted = encrypted
        else:
            db.add(
                Provider(
                    id=item.id,
                    name=item.name,
                    role=item.role,
                    api_key_encrypted=encrypted or "",
                    endpoint=item.endpoint or None,
                    enabled=item.enabled,
                )
            )

    await db.commit()
    return {"success": True}


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    await db.delete(provider)
    await db.commit()
    return {"success": True}
