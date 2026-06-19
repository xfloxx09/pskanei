import json

import httpx

from .base import BaseLLM


class OpenAIProvider(BaseLLM):
    provider_id = "openai"

    def __init__(self, api_key: str, endpoint: str = "https://api.openai.com"):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")

    async def generate_prompt(self, story_title: str, story_summary: str) -> dict:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        from .deepseek import SYSTEM_PROMPT

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"News headline: {story_title}\n\nSummary: {story_summary}"},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,
            "max_tokens": 4000,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.endpoint}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return json.loads(data["choices"][0]["message"]["content"])
