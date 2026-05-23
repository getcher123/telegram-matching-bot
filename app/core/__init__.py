"""Application settings from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "tg-market-watch"
    environment: str = "local"
    log_level: str = "INFO"

    # Telegram
    tg_api_id: int | None = None
    tg_api_hash: str | None = None
    tg_phone: str | None = None

    # Admin API
    admin_api_token: str | None = None

    # Config
    tg_market_watch_config: str = "config/watch.yaml"


settings = Settings()
