from abc import ABC, abstractmethod


class BasePublisher(ABC):
    platform_id: str

    @abstractmethod
    async def publish(self, video_url: str, title: str, caption: str, access_token: str) -> dict:
        """Returns {'post_id': str, 'status': str}"""
        pass
