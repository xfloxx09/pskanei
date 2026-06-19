from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawStory:
    title: str
    url: str
    source: str
    summary: str = ""
    engagement: dict = field(default_factory=dict)
    published_at: datetime | None = None


class BaseScraper(ABC):
    source_id: str

    @abstractmethod
    async def fetch(self, time_window: str) -> list[RawStory]:
        pass
