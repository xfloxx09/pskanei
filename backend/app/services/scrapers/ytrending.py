from datetime import datetime, timezone

import httpx

from ...config import settings
from .base import BaseScraper, RawStory

YOUTUBE_API = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeTrendingScraper(BaseScraper):
    source_id = "ytrending"

    async def fetch(self, time_window: str) -> list[RawStory]:
        if not settings.youtube_api_key:
            return []

        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": "US",
            "maxResults": 50,
            "key": settings.youtube_api_key,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(YOUTUBE_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        stories: list[RawStory] = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            title = (snippet.get("title") or "").strip()
            video_id = item.get("id", "")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

            if not title:
                continue

            stories.append(
                RawStory(
                    title=title,
                    url=url,
                    source=self.source_id,
                    summary=(snippet.get("description") or "")[:500],
                    engagement={
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "channel": snippet.get("channelTitle", ""),
                    },
                    published_at=(
                        datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                        if snippet.get("publishedAt")
                        else datetime.now(timezone.utc)
                    ),
                )
            )
        return stories
