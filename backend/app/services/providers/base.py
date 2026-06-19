from abc import ABC, abstractmethod


class BaseLLM(ABC):
    provider_id: str

    @abstractmethod
    async def generate_prompt(self, story_title: str, story_summary: str) -> dict:
        pass


class BaseTTS(ABC):
    provider_id: str

    @abstractmethod
    async def generate_speech(self, text: str) -> str:
        """Returns URL to generated audio file."""
        pass


class BaseVideo(ABC):
    provider_id: str

    @abstractmethod
    async def render_video(self, prompt: dict, tts_url: str) -> str:
        """Returns URL to rendered video file."""
        pass
