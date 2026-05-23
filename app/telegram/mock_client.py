"""Mock Telegram client for testing."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from app.telegram.client_state import ClientStatus

MessageHandler = Callable[..., Any]


class MockTelegramClientService:
    """Mock client for tests without real Telegram connection."""

    def __init__(self, **kwargs: object) -> None:  # noqa: ARG002
        self._status = ClientStatus.DISCONNECTED
        self.on_message: MessageHandler | None = None

    @property
    def status(self) -> ClientStatus:
        return self._status

    @property
    def is_authorized(self) -> bool:
        return self._status == ClientStatus.AUTHORIZED

    async def start(self) -> None:
        self._status = ClientStatus.AUTHORIZED

    async def send_code(self) -> None:
        pass

    async def confirm_code(self, _code: str) -> None:
        self._status = ClientStatus.AUTHORIZED

    async def confirm_2fa(self, _password: str) -> None:
        self._status = ClientStatus.AUTHORIZED

    async def run_until_disconnected(self) -> None:
        """Block forever in mock."""
        await asyncio.Event().wait()

    async def stop(self) -> None:
        self._status = ClientStatus.DISCONNECTED
