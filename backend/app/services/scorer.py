import math
from datetime import datetime, timezone

from .scrapers.base import RawStory

WINDOW_MINUTES = {"1h": 60, "6h": 360, "12h": 720, "24h": 1440, "3d": 4320}

WEIGHT_RECENCY = 0.35
WEIGHT_CROSS_SOURCE = 0.35
WEIGHT_ENGAGEMENT = 0.30


def _recency_score(story: RawStory, time_window: str) -> float:
    max_min = WINDOW_MINUTES.get(time_window, 360)
    if story.published_at is None:
        return 0.5
    age_min = (datetime.now(timezone.utc) - story.published_at).total_seconds() / 60
    age_min = max(0, age_min)
    decay = max(0.1, 1.0 - (age_min / max_min))
    return round(decay, 3)


def _cross_source_score(merged_count: int) -> float:
    return min(1.0, merged_count / 5.0)


def _engagement_score(engagement: dict) -> float:
    if not engagement:
        return 0.0

    signals: list[float] = []

    # Reddit
    if "ups" in engagement:
        upvotes = engagement["ups"]
        comments = engagement.get("num_comments", 0)
        signals.append(min(1.0, math.log1p(upvotes) / 15.0))
        signals.append(min(1.0, math.log1p(comments) / 12.0))

    # YouTube
    if "views" in engagement:
        views = engagement["views"]
        signals.append(min(1.0, math.log1p(views) / 18.0))

    # GDELT
    if "shares_gdelt" in engagement:
        shares = engagement["shares_gdelt"]
        signals.append(min(1.0, math.log1p(shares) / 6.0))

    if not signals:
        return 0.3  # neutral fallback

    return round(sum(signals) / len(signals), 3)


def score_story(story: RawStory, time_window: str) -> float:
    recency = _recency_score(story, time_window)
    merged_count = story.engagement.get("merged_count", 1)
    cross_source = _cross_source_score(merged_count)
    engagement = _engagement_score(story.engagement)

    composite = (
        WEIGHT_RECENCY * recency
        + WEIGHT_CROSS_SOURCE * cross_source
        + WEIGHT_ENGAGEMENT * engagement
    )
    score = round(composite * 100, 1)

    story.engagement["_score_breakdown"] = {
        "recency": recency,
        "cross_source": cross_source,
        "engagement": engagement,
        "composite": score,
    }

    return score


def score_stories(stories: list[RawStory], time_window: str) -> list[RawStory]:
    for s in stories:
        score_story(s, time_window)
    stories.sort(key=lambda s: s.engagement.get("_score_breakdown", {}).get("composite", 0), reverse=True)
    return stories
