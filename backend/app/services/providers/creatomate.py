import httpx

from .base import BaseVideo

CREATOMATE_API = "https://api.creatomate.com/v1/renders"


class CreatomateProvider(BaseVideo):
    provider_id = "creatomate"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def render_video(self, prompt: dict, tts_url: str) -> str:
        if not self.api_key:
            raise ValueError("Creatomate API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        visual = prompt.get("visual_description", "")
        hook = prompt.get("hook_text", "")
        duration = prompt.get("duration_estimate_seconds", 45)

        source = {
            "output_format": "mp4",
            "width": 1080,
            "height": 1920,
            "elements": [
                {
                    "type": "text",
                    "text": hook,
                    "x": "50%",
                    "y": "25%",
                    "width": "80%",
                    "font_size": 64,
                    "font_weight": "bold",
                    "fill_color": "#ffffff",
                    "stroke_color": "#000000",
                    "stroke_width": 2,
                    "text_align": "center",
                    "animations": [
                        {"type": "fade_in", "duration": 0.5},
                    ],
                },
                {
                    "type": "audio",
                    "source": tts_url,
                    "duration": duration,
                },
            ],
            "duration": duration,
        }

        payload = {"source": source}

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(CREATOMATE_API, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return data.get("url", "") or f"creatomate://render/{data.get('id', 'unknown')}"
