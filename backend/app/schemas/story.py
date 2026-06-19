from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator


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

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_ai(cls, data):
        if hasattr(data, "content"):
            c = getattr(data, "content", None) or {}
            if isinstance(c, dict) and "ai_curation" in c:
                data = dict(data.__dict__) if hasattr(data, "__dict__") else data
                data["ai_curation"] = c["ai_curation"]
        return data
