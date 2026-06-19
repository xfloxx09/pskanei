from datetime import datetime

from pydantic import BaseModel


class SourceItem(BaseModel):
    id: str
    name: str
    desc: str = ""
    enabled: bool = True


class ScrapeSettingsIn(BaseModel):
    window: str
    frequency: str
    sources: list[SourceItem]
    scraper_keys: dict[str, str] = {}


class ScrapeSettingsOut(BaseModel):
    window: str
    frequency: str
    sources: list[SourceItem]
    scraper_keys: dict[str, str] = {}
    updated_at: datetime

    model_config = {"from_attributes": True}
