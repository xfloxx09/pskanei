import json
import uuid

import httpx

CURATOR_PROMPT = """You are a world-class social media strategist and viral content director. Analyze these trending news stories and their full article content to determine which ones would make the most viral short-form vertical videos (YouTube Shorts, TikTok, Instagram Reels).

For each story, evaluate:
- Emotional hook potential (anger, awe, curiosity, fear, joy)
- Shareability (would people send this to friends?)
- Visual potential (can this be illustrated/stylized well?)
- Category fit (finance/tech/politics/entertainment/science/sports/weird)

Read the full article text provided — some may be empty. Use the headline AND article content to judge viral potential.

Return ONLY valid JSON:
{
  "analyses": [
    {
      "id": "the story id",
      "category": "finance",
      "viral_score": 87,
      "hook_angle": "One sentence viral hook for this story",
      "reasoning": "Why this will/won't go viral (max 80 chars)",
      "is_top_pick": false
    }
  ],
  "top_pick_ids": ["id1", "id2", "id3"]
}

Rules:
- viral_score: 0-100. 80+ = very viral, 60-79 = decent potential, <60 = skip
- Only pick top 3 as top_pick_ids
- Be ruthless — most stories are NOT viral. Flag the truly exceptional ones
- Focus on universal human emotions, not niche interests
- Use the full article text to find the most compelling angle"""


async def curate_stories(
    stories: list[dict],
    api_key: str,
    endpoint: str = "https://api.deepseek.com",
    custom_prompt: str = "",
) -> dict:
    if not api_key or not stories:
        return {"analyses": [], "top_pick_ids": []}

    system_prompt = custom_prompt or CURATOR_PROMPT

    story_text = "\n".join(
        f'[id:{s["id"]}] score:{s.get("score",0)} source:{s.get("source","")} | {s["title"]}'
        + (f'\n  Article: {s.get("content","")[:500]}' if s.get("content") else '')
        for s in stories
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze these scraped news stories for viral potential:\n\n{story_text}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": 16000,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{endpoint.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    result = json.loads(content)

    return result
