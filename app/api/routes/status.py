"""Status endpoint — component health and diagnostics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.security import verify_admin_token

router = APIRouter(tags=["status"])


@router.get("/status")
async def get_status(
    request: Request,
    _token: str = Depends(verify_admin_token),  # noqa: B008
) -> dict[str, Any]:
    app_state = getattr(request.app.state, "app_state", None)

    if app_state is None:
        return {
            "status": "starting",
            "telegram_connected": False,
            "authorized": False,
            "active_config_hash": "",
            "enabled_rules": 0,
            "enabled_chats": 0,
            "messages_processed_total": 0,
            "matches_total": 0,
            "alerts_sent_total": 0,
            "alerts_failed_total": 0,
        }

    return {
        "status": "ready",
        "telegram_connected": app_state.telegram_connected,
        "authorized": app_state.telegram_authorized,
        "active_config_hash": (
            app_state.config_version.config_hash if app_state.config_version else ""
        ),
        "enabled_rules": (
            app_state.config_version.enabled_rules_count if app_state.config_version else 0
        ),
        "enabled_chats": 0,
        "messages_processed_total": app_state.messages_processed,
        "matches_total": app_state.matches_total,
        "alerts_sent_total": app_state.alerts_sent,
        "alerts_failed_total": app_state.alerts_failed,
    }
