import asyncio
from datetime import datetime, timezone

import httpx

from .base import BaseScraper, RawStory

GAPI_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_window(window: str) -> int:
    map_ = {"1h": 60, "6h": 360, "12h": 720, "24h": 1440, "3d": 4320}
    return map_.get(window, 360)


async def _fetch_with_retry(client: httpx.AsyncClient, url: str, params: dict, max_retries: int = 3) -> httpx.Response:
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                wait = min(2 ** attempt, 30)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = min(2 ** attempt, 30)
                await asyncio.sleep(wait)
                continue
            raise
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    raise last_exc or RuntimeError("Max retries exceeded")


class GDELTScraper(BaseScraper):
    source_id = "gdelt"

    async def fetch(self, time_window: str) -> list[RawStory]:
        minutes = _parse_window(time_window)
        params = {
            "query": "sourcelang:eng",
            "mode": "artlist",
            "maxrecords": 75,
            "format": "json",
            "timespan": f"{minutes}minutes",
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await _fetch_with_retry(client, GAPI_URL, params)
            data = resp.json()

        raw_articles = (
            data.get("articles")
            or data.get("results")
            or data.get("data")
            or data.get("items")
            or []
        )

        if not raw_articles and isinstance(data, list):
            raw_articles = data

        if not raw_articles:
            names = list(data.keys())[:5] if isinstance(data, dict) else []
            raise RuntimeError(f"GDELT: 0 articles. keys={names}")

        stories: list[RawStory] = []
        for article in raw_articles:
            if not isinstance(article, dict):
                continue
            title = (article.get("title") or article.get("name") or "").strip()
            if not title:
                continue
            url = (article.get("url") or article.get("link") or "").strip()
            stories.append(
                RawStory(
                    title=title,
                    url=url or f"https://news.google.com/search?q={title.replace(' ', '+')}",
                    source=self.source_id,
                    summary=article.get("seendate", article.get("description", "")),
                    engagement={
                        "shares_gdelt": article.get("numarts", 1),
                    },
                    published_at=datetime.now(timezone.utc),
                )
            )

        if not stories:
            keys0 = list(raw_articles[0].keys())[:10] if raw_articles else []
            raise RuntimeError(f"GDELT: {len(raw_articles)} articles, 0 with title. keys: {keys0}")

        return stories
