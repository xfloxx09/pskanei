from datetime import datetime, timezone, timedelta

import httpx

from .base import BaseScraper, RawStory

REDDIT_BASE = "https://www.reddit.com"
SUBREDDITS = ["all", "popular"]
SORTS = ["hot", "top"]


def _parse_window(window: str) -> str:
    map_ = {"1h": "hour", "6h": "hour", "12h": "day", "24h": "day", "3d": "week"}
    return map_.get(window, "day")


class RedditScraper(BaseScraper):
    source_id = "reddit"

    async def fetch(self, time_window: str) -> list[RawStory]:
        t_param = _parse_window(time_window)
        headers = {"User-Agent": "ViralClipStudio/1.0"}

        stories: list[RawStory] = []
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            for sub in SUBREDDITS:
                for sort in SORTS:
                    url = f"{REDDIT_BASE}/r/{sub}/{sort}.json"
                    params = {"t": t_param, "limit": 50, "raw_json": 1}
                    try:
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception:
                        continue

                    for child in data.get("data", {}).get("children", []):
                        post = child.get("data", {})
                        title = (post.get("title") or "").strip()
                        permalink = post.get("permalink", "")
                        url = f"https://www.reddit.com{permalink}" if permalink else ""
                        if not title:
                            continue
                        stories.append(
                            RawStory(
                                title=title,
                                url=url,
                                source=self.source_id,
                                summary=post.get("selftext", "")[:300] or post.get("url_overridden_by_dest", ""),
                                engagement={
                                    "ups": post.get("ups", 0),
                                    "num_comments": post.get("num_comments", 0),
                                    "score": post.get("score", 0),
                                    "subreddit": post.get("subreddit", ""),
                                    "over_18": post.get("over_18", False),
                                },
                                published_at=datetime.fromtimestamp(
                                    post.get("created_utc", 0), tz=timezone.utc
                                ),
                            )
                        )
        return stories
