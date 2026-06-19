import json
from typing import Any

import httpx

from .base import BaseLLM

SYSTEM_PROMPT = """You are a viral short-video script writer. Given a trending news story, produce a structured JSON output for a 30-60 second vertical video (9:16 aspect ratio).

Return ONLY valid JSON with this exact structure:
{
  "visual_description": "Describe the visual sequence in detail: backgrounds, on-screen text elements, transitions. Use stylized/illustrative visuals — never photorealistic depictions of real people.",
  "voiceover_script": "Full voiceover narration script. Keep it fast-paced and engaging.",
  "hook_text": "One bold on-screen text hook that appears in the first 3 seconds.",
  "duration_estimate_seconds": 45,
  "captions": {
    "youtube": {"text": "Caption for YouTube Shorts", "hashtags": ["#trending", "#news"]},
    "tiktok": {"text": "Caption for TikTok", "hashtags": ["#fyp", "#viral"]},
    "instagram": {"text": "Caption for Instagram Reels", "hashtags": ["#reels", "#explore"]},
    "facebook": {"text": "Caption for Facebook Reels", "hashtags": ["#viral", "#trending"]}
  }
}"""


class DeepSeekProvider(BaseLLM):
    provider_id = "deepseek"

    def __init__(self, api_key: str, endpoint: str = "https://api.deepseek.com", system_prompt: str = ""):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self._system_prompt = system_prompt or SYSTEM_PROMPT

    async def generate_prompt(self, story_title: str, story_summary: str) -> dict:
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {
                    "role": "user",
                    "content": f"News headline: {story_title}\n\nSummary: {story_summary}",
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
            "max_tokens": 4000,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
