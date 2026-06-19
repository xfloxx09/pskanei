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
    status_msg: str = ""

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_ai(cls, data):
        if hasattr(data, "content"):
            c = getattr(data, "content", None) or {}
            result = dict(data.__dict__) if hasattr(data, "__dict__") else {}
            if isinstance(c, dict):
                if "ai_curation" in c:
                    result["ai_curation"] = c["ai_curation"]
                if "status_msg" in c:
                    result["status_msg"] = c["status_msg"]
                result["content"] = c
                return result
        return data


class StoryList(BaseModel):
    stories: list[StoryOut]
    total: int


class StoryDetail(StoryOut):
    content: dict | None = None
