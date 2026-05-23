"""Tests for Telegram client service."""

from __future__ import annotations

import pytest

from app.telegram.client_state import ClientStatus
from app.telegram.mock_client import MockTelegramClientService


@pytest.mark.asyncio
async def test_mock_client_start():
    """BL-0201: Mock клиент стартует без ошибок."""
    client = MockTelegramClientService()
    assert client.status == ClientStatus.DISCONNECTED

    await client.start()
    assert client.is_authorized
    assert client.status == ClientStatus.AUTHORIZED


@pytest.mark.asyncio
async def test_mock_client_stop():
    """BL-0201: Mock клиент останавливается."""
    client = MockTelegramClientService()
    await client.start()
    await client.stop()
    assert client.status == ClientStatus.DISCONNECTED


@pytest.mark.asyncio
async def test_mock_client_auth_flow():
    """BL-0202: Полный цикл авторизации mock."""
    client = MockTelegramClientService()
    await client.start()
    assert client.is_authorized

    await client.send_code()
    await client.confirm_code("12345")
    assert client.is_authorized


@pytest.mark.asyncio
async def test_mock_client_2fa():
    """BL-0202: 2FA в mock."""
    client = MockTelegramClientService()
    await client.start()
    await client.confirm_2fa("password123")
    assert client.is_authorized
