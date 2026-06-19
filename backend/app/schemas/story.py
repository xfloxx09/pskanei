from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StoryOut(BaseModel):
    id: UUID
    title: str
    url: str | None = None
    source: str
    source_urls: list[str] = []
    summary: str | None = None
    score: float
    score_breakdown: dict | None = None
    time_window: str
    status: str
    spotted_at: datetime
    ai_curation: dict | None = None
    status_msg: str = ""

    model_config = {"from_attributes": True}


class StoryList(BaseModel):
    stories: list[StoryOut]
    total: int


class StoryDetail(StoryOut):
    content: dict | None = None
