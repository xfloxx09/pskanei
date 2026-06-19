import re
from difflib import SequenceMatcher

from .scrapers.base import RawStory

SIMILARITY_THRESHOLD = 0.85


def _normalize(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(stories: list[RawStory]) -> list[RawStory]:
    if not stories:
        return []

    groups: list[list[RawStory]] = []
    normalized = [_normalize(s.title) for s in stories]

    for i, story in enumerate(stories):
        matched = False
        for group in groups:
            group_norm = _normalize(group[0].title)
            ratio = _similarity(normalized[i], group_norm)
            if ratio >= SIMILARITY_THRESHOLD:
                group.append(story)
                matched = True
                break
        if not matched:
            groups.append([story])

    merged: list[RawStory] = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue

        best = max(
            group,
            key=lambda s: (s.engagement.get("score", 0) or 0)
            + (s.engagement.get("ups", 0) or 0),
        )
        best.url = best.url or group[0].url
        merged_sources: list[str] = []
        for s in group:
            if s.url and s.url not in merged_sources:
                merged_sources.append(s.url)
        best.engagement["merged_sources"] = merged_sources
        best.engagement["merged_count"] = len(group)
        merged.append(best)

    return merged
