import tempfile

from .base import BaseTTS


class EdgeTTSProvider(BaseTTS):
    """
    Free TTS using Microsoft Edge's built-in voices.
    No API key required. High quality, multiple voices.
    """
    provider_id = "edge_tts"

    def __init__(self, voice: str = "en-US-AriaNeural"):
        self.voice = voice

    async def generate_speech(self, text: str) -> str:
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(out_path)

        return f"tts://edge/generated/{hash(text) & 0xFFFFFFFF}.mp3?path={out_path}"
