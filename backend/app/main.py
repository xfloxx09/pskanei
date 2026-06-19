import os

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import engine, Base, get_db
from .models import Story, ScrapeSettings, Provider, PlatformAccount, PublishedClip  # noqa: F401
from .routers import queue_router, scrape_router, providers_router, platforms_router, auth_router, schedule_router
from .services.budget import get_spent_today, get_daily_budget


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns missing from earlier deploys
        await conn.run_sync(_run_migrations)
    yield
    await engine.dispose()


def _run_migrations(conn):
    from sqlalchemy import text
    try:
        conn.execute(text("ALTER TABLE scrape_settings ADD COLUMN IF NOT EXISTS scraper_keys JSONB DEFAULT '{}' NOT NULL"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE scrape_settings ADD COLUMN IF NOT EXISTS prompt_templates JSONB DEFAULT '{}' NOT NULL"))
    except Exception:
        pass


app = FastAPI(
    title="Viral Clip Studio",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queue_router)
app.include_router(scrape_router)
app.include_router(providers_router)
app.include_router(platforms_router)
app.include_router(auth_router)
app.include_router(schedule_router)


@app.get("/api/status")
async def status(db: AsyncSession = Depends(get_db)):
    async def _count(st: str) -> int:
        r = await db.execute(
            select(func.count(Story.id)).where(Story.status == st)
        )
        return r.scalar() or 0

    return {
        "pending": await _count("pending"),
        "generating": await _count("generating"),
        "ready": await _count("ready"),
        "budget_used_today": await get_spent_today(db),
        "daily_budget": await get_daily_budget(db),
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Serve frontend static files (after all API routes) ---

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend():
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"status": "ok", "message": "API running, frontend not built"}
