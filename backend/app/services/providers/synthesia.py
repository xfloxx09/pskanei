import httpx

from .base import BaseVideo


class SynthesiaProvider(BaseVideo):
    provider_id = "synthesia"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def render_video(self, prompt: dict, tts_url: str) -> str:
        if not self.api_key:
            raise ValueError("Synthesia API key not configured")

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        voiceover = prompt.get("voiceover_script", "")
        hook = prompt.get("hook_text", "")

        payload = {
            "test": True,
            "input": [
                {
                    "scriptText": hook + "\n\n" + voiceover,
                    "avatar": "anna_costume1_cameraA",
                    "background": "green_screen",
                }
            ],
            "title": hook[:80],
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.synthesia.io/v2/videos",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("id", "") or f"synthesia://video/{data.get('id', 'unknown')}"
