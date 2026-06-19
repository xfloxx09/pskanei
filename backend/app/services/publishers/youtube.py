import json

import httpx

from .base import BasePublisher

YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubePublisher(BasePublisher):
    platform_id = "youtube"

    async def publish(self, video_url: str, title: str, caption: str, access_token: str) -> dict:
        if not access_token:
            raise ValueError("YouTube access token not configured")

        async with httpx.AsyncClient(timeout=120) as http:
            download_resp = await http.get(video_url)
            download_resp.raise_for_status()
            video_bytes = download_resp.content

        metadata = {
            "snippet": {
                "title": title[:100],
                "description": caption,
                "categoryId": "25",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=180) as http:
            init_resp = await http.post(
                f"{YOUTUBE_UPLOAD_URL}?part=snippet,status&uploadType=resumable",
                headers={**headers, "Content-Type": "application/json"},
                json=metadata,
            )
            init_resp.raise_for_status()
            upload_url = init_resp.headers.get("Location", "")

            if upload_url:
                upload_resp = await http.put(
                    upload_url,
                    headers=headers,
                    content=video_bytes,
                )
                upload_resp.raise_for_status()
                result = upload_resp.json()
            else:
                result = init_resp.json()

        post_id = result.get("id", "")
        return {"post_id": post_id, "status": "published", "url": f"https://www.youtube.com/shorts/{post_id}"}
