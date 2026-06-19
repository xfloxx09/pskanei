import httpx

from .base import BaseVideo

SHOTSTACK_API = "https://api.shotstack.io/v1/render"


class ShotstackProvider(BaseVideo):
    provider_id = "shotstack"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def render_video(self, prompt: dict, tts_url: str) -> str:
        if not self.api_key:
            raise ValueError("Shotstack API key not configured")

        hook = prompt.get("hook_text", "")
        voiceover = prompt.get("voiceover_script", "")
        duration = prompt.get("duration_estimate_seconds", 45)

        payload = {
            "timeline": {
                "soundtrack": {"src": tts_url, "effect": "fadeInFadeOut"},
                "tracks": [
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "html",
                                    "html": f"<div style='width:100%;height:100%;background:linear-gradient(135deg,#1a1a2e,#16213e);display:flex;align-items:center;justify-content:center;color:white;font-family:sans-serif;font-size:48px;font-weight:bold;text-align:center;padding:40px'>{hook}</div>",
                                },
                                "start": 0,
                                "length": duration,
                            }
                        ]
                    }
                ],
            },
            "output": {
                "format": "mp4",
                "resolution": "vertical",
                "aspectRatio": "9:16",
            },
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(SHOTSTACK_API, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        render_id = data.get("response", {}).get("id", "")
        return f"shotstack://render/{render_id}" if render_id else f"shotstack://queued"
