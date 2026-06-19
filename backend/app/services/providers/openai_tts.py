import httpx

from .base import BaseTTS


class OpenAITTSProvider(BaseTTS):
    provider_id = "openai_tts"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_speech(self, text: str) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        payload = {
            "model": "tts-1",
            "input": text,
            "voice": "alloy",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            audio_bytes = resp.content

        size = len(audio_bytes) if audio_bytes else 0
        return f"tts://openai/generated/{hash(text) & 0xFFFFFFFF}.mp3?size={size}"
