from datetime import datetime, timezone

import httpx

from ...config import settings
from .base import BaseScraper, RawStory

NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


class NewsAPIScraper(BaseScraper):
    source_id = "newsapi"

    async def fetch(self, time_window: str) -> list[RawStory]:
        if not settings.newsapi_key:
            return []

        params = {
            "apiKey": settings.newsapi_key,
            "language": "en",
            "pageSize": 100,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(NEWSAPI_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        stories: list[RawStory] = []
        for article in data.get("articles", []):
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url:
                continue
            stories.append(
                RawStory(
                    title=title,
                    url=url,
                    source=self.source_id,
                    summary=(article.get("description") or "")[:500],
                    engagement={
                        "source_name": (article.get("source", {}).get("name") or ""),
                    },
                    published_at=(
                        datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                        if article.get("publishedAt")
                        else datetime.now(timezone.utc)
                    ),
                )
            )
        return stories
