from datetime import datetime, timezone

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
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ViralClipStudio/1.0; by /u/xfloxx09)",
            "Accept": "application/json",
        }

        stories: list[RawStory] = []
        errors = []
        response_preview = ""

        async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as client:
            for sub in SUBREDDITS:
                for sort in SORTS:
                    url = f"{REDDIT_BASE}/r/{sub}/{sort}.json"
                    params = {"t": t_param, "limit": 50}
                    try:
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        text = resp.text
                        if not response_preview:
                            response_preview = f"r/{sub}/{sort} status={resp.status_code} body={text[:250]}"

                        if not text.strip():
                            continue

                        data = resp.json()

                        children = []
                        if isinstance(data, dict):
                            children = (
                                data.get("data", {}).get("children", [])
                                or data.get("children", [])
                            )
                        elif isinstance(data, list):
                            children = data

                        for child in children:
                            if not isinstance(child, dict):
                                continue
                            post = child.get("data", child)
                            title = (post.get("title") or "").strip()
                            if not title:
                                continue
                            permalink = post.get("permalink", "")
                            post_url = f"https://www.reddit.com{permalink}" if permalink else post.get("url", post.get("url_overridden_by_dest", ""))
                            stories.append(
                                RawStory(
                                    title=title,
                                    url=post_url,
                                    source=self.source_id,
                                    summary=post.get("selftext", "")[:300] or post.get("url_overridden_by_dest", ""),
                                    engagement={
                                        "ups": post.get("ups", post.get("score", 0)),
                                        "num_comments": post.get("num_comments", 0),
                                        "subreddit": post.get("subreddit", ""),
                                    },
                                    published_at=datetime.fromtimestamp(
                                        post.get("created_utc", 0), tz=timezone.utc
                                    ),
                                )
                            )
                    except httpx.HTTPStatusError as exc:
                        errors.append(f"r/{sub}/{sort}: HTTP {exc.response.status_code}")
                    except Exception as exc:
                        errors.append(f"r/{sub}/{sort}: {exc}")

        if not stories:
            detail = f"preview: {response_preview}"
            if errors:
                detail += " | errors: " + "; ".join(errors)
            raise RuntimeError(detail)

        return stories
