from .base import BaseScraper, RawStory
from .gdelt import GDELTScraper
from .reddit import RedditScraper
from .newsapi import NewsAPIScraper
from .gtrends import GoogleTrendsScraper
from .ytrending import YouTubeTrendingScraper

__all__ = [
    "BaseScraper",
    "RawStory",
    "GDELTScraper",
    "RedditScraper",
    "NewsAPIScraper",
    "GoogleTrendsScraper",
    "YouTubeTrendingScraper",
]
