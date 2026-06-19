from .queue import router as queue_router
from .scrape import router as scrape_router
from .providers import router as providers_router
from .platforms import router as platforms_router
from .auth import router as auth_router
from .schedule import router as schedule_router

__all__ = [
    "queue_router",
    "scrape_router",
    "providers_router",
    "platforms_router",
    "auth_router",
    "schedule_router",
]
