import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/viral_clip_studio"

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Scraper API Keys ---
    newsapi_key: str = ""
    youtube_api_key: str = ""
    gdelt_api_key: str = ""

    # --- Provider API Keys (Phase 2+) ---
    deepseek_api_key: str = ""
    creatomate_api_key: str = ""
    elevenlabs_api_key: str = ""
    heygen_api_key: str = ""

    # --- OAuth (Phase 3) ---
    youtube_client_id: str = ""
    youtube_client_secret: str = ""

    # --- Storage ---
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_endpoint: str = ""

    # --- App ---
    secret_key: str = "change-me"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
