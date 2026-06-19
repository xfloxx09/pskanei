from datetime import datetime, timezone

from .base import BaseScraper, RawStory


class GoogleTrendsScraper(BaseScraper):
    source_id = "gtrends"

    async def fetch(self, time_window: str) -> list[RawStory]:
        # pytrends requires a separate pip install (pytrends).
        # Placeholder — returns empty until wired with real credentials / setup.
        return []
