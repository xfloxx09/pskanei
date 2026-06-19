from datetime import datetime, timezone

import httpx

from .base import BaseScraper, RawStory

OAUTH_BASE = "https://oauth.reddit.com"
PUBLIC_BASE = "https://www.reddit.com"
SUBREDDITS = ["all", "popular"]
SORTS = ["hot", "top"]


def _parse_window(window: str) -> str:
    map_ = {"1h": "hour", "6h": "hour", "12h": "day", "24h": "day", "3d": "week"}
    return map_.get(window, "day")


class RedditScraper(BaseScraper):
    source_id = "reddit"

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self._client_id = client_id
        self._client_secret = client_secret

    async def _get_oauth_client(self) -> tuple[httpx.AsyncClient, str]:
        if not self._client_id or not self._client_secret:
            return None, PUBLIC_BASE

        import base64
        auth = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()

        client = httpx.AsyncClient(timeout=30, follow_redirects=True)
        resp = await client.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {auth}",
                "User-Agent": "ViralClipStudio/1.0 (by /u/xfloxx09)",
            },
        )
        if resp.status_code != 200:
            await client.aclose()
            return None, PUBLIC_BASE

        token = resp.json().get("access_token", "")
        if not token:
            await client.aclose()
            return None, PUBLIC_BASE

        client.headers["Authorization"] = f"Bearer {token}"
        return client, OAUTH_BASE

    async def fetch(self, time_window: str) -> list[RawStory]:
        t_param = _parse_window(time_window)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ViralClipStudio/1.0)",
            "Accept": "application/json",
        }

        oauth_client, base_url = await self._get_oauth_client()
        if oauth_client:
            client = oauth_client
        else:
            client = httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True)

        stories: list[RawStory] = []
        errors = []

        try:
            for sub in SUBREDDITS:
                for sort in SORTS:
                    url = f"{base_url}/r/{sub}/{sort}.json"
                    params = {"t": t_param, "limit": 50}
                    try:
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        data = resp.json()

                        children = data.get("data", {}).get("children", [])
                        if isinstance(data, list):
                            children = data

                        for child in children:
                            if not isinstance(child, dict):
                                continue
                            post = child.get("data", child)
                            title = (post.get("title") or "").strip()
                            if not title:
                                continue
                            permalink = post.get("permalink", "")
                            post_url = f"https://www.reddit.com{permalink}" if permalink else ""
                            stories.append(
                                RawStory(
                                    title=title,
                                    url=post_url or post.get("url", ""),
                                    source=self.source_id,
                                    summary=(post.get("selftext", "") or "")[:300],
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
        finally:
            await client.aclose()

        if not stories:
            preview = f"base={base_url}"
            if errors:
                preview += " | " + "; ".join(errors)
            raise RuntimeError(preview)

        return stories
