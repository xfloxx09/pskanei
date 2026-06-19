import httpx

from .base import BasePublisher

META_API_BASE = "https://graph.facebook.com/v21.0"


class InstagramPublisher(BasePublisher):
    platform_id = "instagram"

    async def publish(self, video_url: str, title: str, caption: str, access_token: str) -> dict:
        if not access_token:
            raise ValueError("Instagram access token not configured")

        async with httpx.AsyncClient(timeout=120) as http:
            me_resp = await http.get(
                f"{META_API_BASE}/me/accounts",
                params={"access_token": access_token},
            )
            me_resp.raise_for_status()
            pages = me_resp.json().get("data", [])
            if not pages:
                raise ValueError("No Instagram business account found")

            page_id = pages[0]["id"]
            page_token = pages[0]["access_token"]

            ig_resp = await http.get(
                f"{META_API_BASE}/{page_id}",
                params={"fields": "instagram_business_account", "access_token": page_token},
            )
            ig_resp.raise_for_status()
            ig_data = ig_resp.json()
            ig_user_id = ig_data.get("instagram_business_account", {}).get("id")
            if not ig_user_id:
                raise ValueError("No Instagram business account linked to page")

            container_resp = await http.post(
                f"{META_API_BASE}/{ig_user_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "access_token": page_token,
                },
            )
            container_resp.raise_for_status()
            container_id = container_resp.json().get("id", "")

            publish_resp = await http.post(
                f"{META_API_BASE}/{ig_user_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": page_token,
                },
            )
            publish_resp.raise_for_status()
            post_id = publish_resp.json().get("id", "")

        return {"post_id": post_id, "status": "published"}


class FacebookPublisher(BasePublisher):
    platform_id = "facebook"

    async def publish(self, video_url: str, title: str, caption: str, access_token: str) -> dict:
        if not access_token:
            raise ValueError("Facebook access token not configured")

        async with httpx.AsyncClient(timeout=120) as http:
            me_resp = await http.get(
                f"{META_API_BASE}/me/accounts",
                params={"access_token": access_token},
            )
            me_resp.raise_for_status()
            pages = me_resp.json().get("data", [])
            if not pages:
                raise ValueError("No Facebook page found")

            page_id = pages[0]["id"]
            page_token = pages[0]["access_token"]

            publish_resp = await http.post(
                f"{META_API_BASE}/{page_id}/videos",
                params={
                    "file_url": video_url,
                    "description": f"{title}\n\n{caption}",
                    "access_token": page_token,
                },
            )
            publish_resp.raise_for_status()
            post_id = publish_resp.json().get("id", "")

        return {"post_id": post_id, "status": "published"}
