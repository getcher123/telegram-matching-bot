"""App settings from environment via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = "dev-secret"
    admin_api_token: str | None = "dev-secret"
    api_key_header: str = "Authorization"

    tg_phone: str = ""
    tg_api_id: int = 0
    tg_api_hash: str = ""
    tg_session_file: str = "var/telegram/session"

    debug: bool = False


settings = AppSettings()
