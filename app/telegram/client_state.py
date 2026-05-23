"""Telegram user-client states."""

from __future__ import annotations

from enum import StrEnum


class ClientStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AWAITING_CODE = "awaiting_code"
    AWAITING_2FA = "awaiting_2fa"
    AUTHORIZED = "authorized"
    ERROR = "error"
