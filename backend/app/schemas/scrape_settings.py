from datetime import datetime

from pydantic import BaseModel


class SourceItem(BaseModel):
    id: str
    name: str
    desc: str = ""
    enabled: bool = True


class ScrapeSettingsIn(BaseModel):
    window: str  # "1h", "6h", "12h", "24h", "3d"
    frequency: str  # "15", "30", "60"
    sources: list[SourceItem]


class ScrapeSettingsOut(BaseModel):
    window: str
    frequency: str
    sources: list[SourceItem]
    updated_at: datetime

    model_config = {"from_attributes": True}
