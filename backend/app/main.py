from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import engine, Base, get_db
from .models import Story, ScrapeSettings  # ensure tables are registered  # noqa: F401
from .routers import queue_router, scrape_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Viral Clip Studio",
    version="0.1.0",
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
        "budget_used_today": 0,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
