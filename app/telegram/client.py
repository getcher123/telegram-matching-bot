"""Telegram user-client service using Telethon."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.events import NewMessage
from telethon.tl.types import Message

from app.telegram.client_state import ClientStatus

logger = logging.getLogger(__name__)

MessageHandler = Callable[[Message, str], Any]


class TelethonClientService:
    """Manages Telethon client lifecycle and message processing."""

    def __init__(
        self,
        session_file: str = "./var/telegram/session.marketwatch",
        api_id: int = 0,
        api_hash: str = "",
        phone: str = "",
        *,
        connect_timeout: int = 20,
        request_timeout: int = 30,
        sequential_updates: bool = True,
        process_new_messages: bool = True,
        process_edited_messages: bool = True,
        ignore_outgoing: bool = True,
    ) -> None:
        self._session_file = session_file
        self._api_id = api_id
        self._api_hash = api_hash
        self._phone = phone
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._sequential_updates = sequential_updates
        self._process_new_messages = process_new_messages
        self._process_edited_messages = process_edited_messages
        self._ignore_outgoing = ignore_outgoing

        self._client: TelegramClient | None = None
        self._status = ClientStatus.DISCONNECTED
        self._authorization_code: str | None = None
        self._password: str | None = None
        self._authorization_event: asyncio.Event = asyncio.Event()

        # External message handler (set by orchestrator)
        self.on_message: MessageHandler | None = None

    @property
    def status(self) -> ClientStatus:
        return self._status

    @property
    def is_authorized(self) -> bool:
        return self._status == ClientStatus.AUTHORIZED

    @property
    def is_connected(self) -> bool:
        return self._status in (ClientStatus.CONNECTED, ClientStatus.AUTHORIZED)

    def _ensure_dirs(self) -> None:
        """Create session directory if needed."""
        session_path = os.path.dirname(self._session_file)
        if session_path:
            os.makedirs(session_path, exist_ok=True)

    async def _handle_new_message(self, event: NewMessage.Event) -> None:
        """Handle an incoming new/edited message."""
        message = event.message
        if self._ignore_outgoing and message.out:
            return

        if self.on_message:
            chat_peer = await self._resolve_chat_peer(message)
            await self.on_message(message, chat_peer)

    async def _resolve_chat_peer(self, msg: Message) -> str:
        """Resolve chat peer identifier."""
        try:
            sender = await msg.get_chat()
            if hasattr(sender, "username") and sender.username:
                return f"@{sender.username}"
            if hasattr(sender, "id"):
                return str(sender.id)
        except Exception:
            logger.debug("Could not resolve chat peer for message %s", msg.id)
        return str(msg.chat_id)

    async def start(self) -> None:
        """Start the Telethon client: connect and authorize."""
        self._ensure_dirs()

        self._client = TelegramClient(
            self._session_file,
            self._api_id,
            self._api_hash,
            sequential_updates=self._sequential_updates,
            request_retries=3,
            connection_retries=3,
            timeout=self._request_timeout,
        )

        self._status = ClientStatus.CONNECTING

        try:
            await self._client.connect()
            self._status = ClientStatus.CONNECTED
        except Exception:
            self._status = ClientStatus.ERROR
            logger.exception("Failed to connect Telethon client")
            raise

        # Check if already authorized
        if await self._client.is_user_authorized():
            self._status = ClientStatus.AUTHORIZED
            self._authorization_event.set()
            logger.info("Telethon client already authorized")
        else:
            self._status = ClientStatus.AWAITING_CODE
            logger.info("Telethon client needs authorization code")

        # Register event handlers
        if self._process_new_messages:
            self._client.on(NewMessage)(self._handle_new_message)

    async def send_code(self) -> None:
        """Request login code from Telegram."""
        if self._client is None:
            raise RuntimeError("Client not started")
        if self._status != ClientStatus.AWAITING_CODE:
            raise RuntimeError(f"Cannot send code in status {self._status}")

        await self._client.send_code_request(self._phone)
        logger.info("Authorization code sent to %s", self._phone)

    async def confirm_code(self, code: str) -> None:
        """Confirm login code."""
        if self._client is None:
            raise RuntimeError("Client not started")
        if self._status != ClientStatus.AWAITING_CODE:
            # Already authorized
            return

        try:
            await self._client.sign_in(phone=self._phone, code=code)
            self._status = ClientStatus.AUTHORIZED
            self._authorization_event.set()
            logger.info("Telethon client authorized successfully")
        except SessionPasswordNeededError:
            self._status = ClientStatus.AWAITING_2FA
            logger.info("2FA password required")
        except (PhoneCodeInvalidError, PhoneCodeExpiredError):
            logger.warning("Invalid or expired code")
            raise

    async def confirm_2fa(self, password: str) -> None:
        """Confirm 2FA password."""
        if self._client is None:
            raise RuntimeError("Client not started")
        if self._status != ClientStatus.AWAITING_2FA:
            raise RuntimeError(f"Cannot confirm 2FA in status {self._status}")

        await self._client.sign_in(password=password)
        self._status = ClientStatus.AUTHORIZED
        self._authorization_event.set()
        logger.info("Telethon client authorized with 2FA")

    async def run_until_disconnected(self) -> None:
        """Keep client running until disconnected."""
        if self._client is None:
            raise RuntimeError("Client not started")

        await self._authorization_event.wait()
        logger.info("Telethon client entering update loop")
        await self._client.run_until_disconnected()

    async def send_message(self, text: str, chat_id: str | None = None) -> bool:
        """Send a message to a chat.

        Implements the AlertSender protocol.
        If chat_id is None, sends to the first configured alert target.
        """
        if self._client is None:
            logger.error("Cannot send message: client not started")
            return False
        if self._status != ClientStatus.AUTHORIZED:
            logger.error("Cannot send message: client not authorized")
            return False

        target = chat_id or self._phone
        try:
            await self._client.send_message(target, text)
            return True
        except Exception:
            logger.exception("Failed to send message to %s", target)
            return False

    async def stop(self) -> None:
        """Disconnect the Telethon client."""
        if self._client:
            await self._client.disconnect()
            self._status = ClientStatus.DISCONNECTED
            logger.info("Telethon client disconnected")