import httpx

from .base import BasePublisher

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


class TikTokPublisher(BasePublisher):
    platform_id = "tiktok"

    async def publish(self, video_url: str, title: str, caption: str, access_token: str) -> dict:
        if not access_token:
            raise ValueError("TikTok access token not configured")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as http:
            download_resp = await http.get(video_url)
            download_resp.raise_for_status()
            video_bytes = download_resp.content

        body = {
            "post_info": {
                "title": title[:150],
                "privacy_level": "SELF_ONLY",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            },
        }

        async with httpx.AsyncClient(timeout=60) as http:
            init_resp = await http.post(
                f"{TIKTOK_API_BASE}/post/publish/video/init/",
                headers=headers,
                json=body,
            )
            init_resp.raise_for_status()
            result = init_resp.json()

        data = result.get("data", {})
        post_id = data.get("publish_id", "")

        return {
            "post_id": post_id,
            "status": "publishing",
            "url": f"https://www.tiktok.com/@user/video/{post_id}",
        }
