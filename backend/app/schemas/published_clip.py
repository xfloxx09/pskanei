from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PublishedClipOut(BaseModel):
    id: UUID
    title: str = ""
    platform: str
    status: str
    when: str = ""
    scheduled_at: datetime | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublishRequest(BaseModel):
    platforms: list[str]  # ["youtube", "tiktok", ...]


class ScheduleRequest(BaseModel):
    platforms: list[str]
    scheduled_at: datetime
