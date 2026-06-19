import httpx

from .base import BaseVideo

JSON2VIDEO_API = "https://api.json2video.com/v2/movies"


class JSON2VideoProvider(BaseVideo):
    provider_id = "json2video"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def render_video(self, prompt: dict, tts_url: str) -> str:
        if not self.api_key:
            raise ValueError("JSON2Video API key not configured")

        hook = prompt.get("hook_text", "")
        duration = prompt.get("duration_estimate_seconds", 45)

        payload = {
            "resolution": "vertical",
            "quality": "high",
            "scenes": [
                {
                    "elements": [
                        {
                            "type": "text",
                            "text": hook,
                            "style": "bold",
                            "font-size": 64,
                            "color": "#ffffff",
                            "background-color": "#1a1a2e",
                            "position": "center",
                            "width": "80%",
                        },
                        {
                            "type": "audio",
                            "src": tts_url,
                        },
                    ],
                    "duration": duration,
                }
            ],
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(JSON2VIDEO_API, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        project_id = data.get("project", "")
        return f"json2video://{project_id}" if project_id else f"json2video://queued"
