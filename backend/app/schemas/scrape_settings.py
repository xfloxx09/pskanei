from datetime import datetime

from pydantic import BaseModel


class SourceItem(BaseModel):
    id: str
    name: str
    desc: str = ""
    enabled: bool = True


class ScrapeSettingsIn(BaseModel):
    window: str
    frequency: str
    sources: list[SourceItem]
    scraper_keys: dict[str, str] = {}


class ScrapeSettingsOut(BaseModel):
    window: str
    frequency: str
    sources: list[SourceItem]
    scraper_keys: dict[str, str] = {}
    prompt_templates: dict[str, str] = {}
    updated_at: datetime

    model_config = {"from_attributes": True}


DEFAULT_PROMPT_TEMPLATES = {
    "curator": "You are a world-class social media strategist and viral content director. Analyze these trending news headlines and determine which ones would make the most viral short-form vertical videos (YouTube Shorts, TikTok, Instagram Reels).\n\nFor each story, evaluate:\n- Emotional hook potential (anger, awe, curiosity, fear, joy)\n- Shareability (would people send this to friends?)\n- Visual potential (can this be illustrated/stylized well?)\n- Category fit (finance/tech/politics/entertainment/science/sports/weird)\n\nReturn ONLY valid JSON:\n{\n  \"analyses\": [\n    {\n      \"id\": \"the story id\",\n      \"category\": \"finance\",\n      \"viral_score\": 87,\n      \"hook_angle\": \"One sentence viral hook for this story\",\n      \"reasoning\": \"Why this will/won't go viral (max 80 chars)\",\n      \"is_top_pick\": false\n    }\n  ],\n  \"top_pick_ids\": [\"id1\", \"id2\", \"id3\"]\n}\n\nRules:\n- viral_score: 0-100. 80+ = very viral, 60-79 = decent potential, <60 = skip\n- Only pick top 3 as top_pick_ids\n- Be ruthless — most stories are NOT viral. Flag the truly exceptional ones\n- Focus on universal human emotions, not niche interests",
    "generator": "You are a viral short-video script writer. Given a trending news story, produce a structured JSON output for a 30-60 second vertical video (9:16 aspect ratio).\n\nReturn ONLY valid JSON with this exact structure:\n{\n  \"visual_description\": \"Describe the visual sequence in detail: backgrounds, on-screen text elements, transitions. Use stylized/illustrative visuals — never photorealistic depictions of real people.\",\n  \"voiceover_script\": \"Full voiceover narration script. Keep it fast-paced and engaging.\",\n  \"hook_text\": \"One bold on-screen text hook that appears in the first 3 seconds.\",\n  \"duration_estimate_seconds\": 45,\n  \"captions\": {\n    \"youtube\": {\"text\": \"Caption for YouTube Shorts\", \"hashtags\": [\"#trending\", \"#news\"]},\n    \"tiktok\": {\"text\": \"Caption for TikTok\", \"hashtags\": [\"#fyp\", \"#viral\"]},\n    \"instagram\": {\"text\": \"Caption for Instagram Reels\", \"hashtags\": [\"#reels\", \"#explore\"]},\n    \"facebook\": {\"text\": \"Caption for Facebook Reels\", \"hashtags\": [\"#viral\", \"#trending\"]}\n  }\n}",
}
