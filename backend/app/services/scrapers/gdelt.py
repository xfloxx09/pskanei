from datetime import datetime, timezone, timedelta

import httpx

from .base import BaseScraper, RawStory

GAPI_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_window(window: str) -> int:
    map_ = {"1h": 60, "6h": 360, "12h": 720, "24h": 1440, "3d": 4320}
    return map_.get(window, 360)


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
            resp = await client.get(GAPI_URL, params=params)
            resp.raise_for_status()
            text = resp.text
            data = resp.json()

        raw_articles = (
            data.get("articles")
            or data.get("results")
            or data.get("data")
            or data.get("items")
            or []
        )

        if not raw_articles:
            if isinstance(data, list):
                raw_articles = data
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list) and len(v) > 0:
                        raw_articles = v
                        break

        if not raw_articles:
            keys = list(data.keys()) if isinstance(data, dict) else None
            raise RuntimeError(
                f"GDELT: 0 articles. keys={keys}, text={text[:400]}"
            )

        stories: list[RawStory] = []
        for article in raw_articles:
            if not isinstance(article, dict):
                continue
            title = (
                (article.get("title") or article.get("name") or "").strip()
            )
            url = (
                article.get("url")
                or article.get("link")
                or article.get("url_mobile")
                or ""
            ).strip()

            if not title:
                continue

            tone = article.get("tone", {})
            stories.append(
                RawStory(
                    title=title,
                    url=url or f"https://news.google.com/search?q={title.replace(' ', '+')}",
                    source=self.source_id,
                    summary=article.get("seendate", article.get("description", "")),
                    engagement={
                        "tone_avg": tone.get("tone", 0) if isinstance(tone, dict) else 0,
                        "shares_gdelt": article.get("numarts", 1),
                    },
                    published_at=datetime.now(timezone.utc),
                )
            )

        if not stories:
            first = raw_articles[0] if raw_articles else {}
            raise RuntimeError(
                f"GDELT: {len(raw_articles)} articles but all filtered (need title). First keys: {list(first.keys()) if isinstance(first, dict) else 'not dict'}"
            )

        return stories
