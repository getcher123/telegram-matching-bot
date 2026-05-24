"""App state shared across components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.alerts.dispatcher import AlertDispatcher
from app.config.loader import ConfigService
from app.core.models import ConfigVersion
from app.engine.pipeline import ProcessingPipeline
from app.storage.database import DatabaseManager
from app.storage.repository import Repository
from app.telegram.client import TelethonClientService


@dataclass
class AppState:
    config_version: ConfigVersion = field(
        default_factory=lambda: ConfigVersion(config_hash="", version=0)
    )
    telegram_connected: bool = False
    telegram_authorized: bool = False
    messages_processed: int = 0
    matches_total: int = 0
    alerts_sent: int = 0
    alerts_failed: int = 0
    component_status: dict[str, Any] = field(default_factory=dict)

    # Services (set during lifespan)
    config_service: ConfigService | None = None
    database: DatabaseManager | None = None
    repository: Repository | None = None
    pipeline: ProcessingPipeline | None = None
    telegram_client: TelethonClientService | None = None
    alert_dispatcher: AlertDispatcher | None = None
