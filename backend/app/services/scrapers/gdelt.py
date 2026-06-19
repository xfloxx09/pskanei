from datetime import datetime, timezone, timedelta

import httpx

from .base import BaseScraper, RawStory


GAPI_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_window(window: str) -> int:
    """Return minutes since start of window."""
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

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(GAPI_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        stories: list[RawStory] = []
        for article in data.get("articles", []):
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url:
                continue
            tone = article.get("tone", {})
            stories.append(
                RawStory(
                    title=title,
                    url=url,
                    source=self.source_id,
                    summary=article.get("seendate", ""),
                    engagement={
                        "tone_avg": tone.get("tone", 0),
                        "tone_pos": tone.get("positive_score", 0),
                        "tone_neg": tone.get("negative_score", 0),
                        "shares_gdelt": article.get("numarts", 1),
                    },
                    published_at=datetime.now(timezone.utc),
                )
            )
        return stories
