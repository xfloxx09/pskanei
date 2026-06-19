import httpx

from .base import BaseTTS

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsProvider(BaseTTS):
    provider_id = "elevenlabs"

    def __init__(self, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        self.api_key = api_key
        self.voice_id = voice_id

    async def generate_speech(self, text: str) -> str:
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")

        url = f"{ELEVENLABS_API}/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

            audio_bytes = resp.content

        # Placeholder: in production, upload audio to R2/S3 and return URL.
        # For now, return a mock URL pointing to the audio file length.
        audio_size = len(audio_bytes) if audio_bytes else 0
        return f"tts://elevenlabs/generated/{self.voice_id}/{hash(text) & 0xFFFFFFFF}.mp3?size={audio_size}"
