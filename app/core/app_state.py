"""App state shared across components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.models import ConfigVersion


@dataclass
class AppState:
    config_version: ConfigVersion = field(default_factory=lambda: ConfigVersion(config_hash="", version=0))
    telegram_connected: bool = False
    telegram_authorized: bool = False
    messages_processed: int = 0
    matches_total: int = 0
    alerts_sent: int = 0
    alerts_failed: int = 0
    component_status: dict[str, Any] = field(default_factory=dict)