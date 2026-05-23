"""Alert dispatcher — formats and sends match notifications."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.engine.rules import RuleDecision

logger = logging.getLogger(__name__)


class AlertSender(Protocol):
    """Protocol for sending alerts to Telegram."""

    async def send_message(self, text: str, chat_id: str | None = None) -> bool: ...


@dataclass
class AlertTemplate:
    rule_id: str
    template: str
    enabled: bool = True


TEMPLATES: dict[str, str] = {
    "default_market_match": (
        "⚡ *Совпадение:* {rule_title}\n"
        "📄 *Сообщение:* {raw_text:.200}\n"
        "🔗 {message_link}\n"
        "📊 *Счёт:* {score} / {threshold}"
    ),
    "short_match": "⚡ {rule_title}: {raw_text:.100}\n🔗 {message_link}",
}


class AlertDispatcher:
    """Formats and dispatches match alerts."""

    def __init__(self, sender: AlertSender | None = None) -> None:
        self._sender = sender

    def set_sender(self, sender: AlertSender) -> None:
        self._sender = sender

    def format_alert(
        self,
        decision: RuleDecision,
        raw_text: str,
        message_link: str,
        template_id: str = "default_market_match",
    ) -> str:
        """Format a match decision into alert text."""
        template = TEMPLATES.get(template_id, TEMPLATES["default_market_match"])
        return template.format(
            rule_title=decision.rule_title or decision.rule_id,
            raw_text=raw_text,
            message_link=message_link,
            score=int(decision.score),
            threshold=decision.threshold,
        )

    async def dispatch(
        self,
        decision: RuleDecision,
        raw_text: str,
        message_link: str,
        target_chat: str | None = None,
    ) -> bool:
        """Format and dispatch a single alert."""
        if not self._sender:
            logger.warning("No alert sender configured, alert not dispatched")
            return False

        text = self.format_alert(decision, raw_text, message_link)
        try:
            ok = await self._sender.send_message(text, target_chat)
            if ok:
                logger.info("Alert dispatched for rule %s", decision.rule_id)
            return ok
        except Exception:
            logger.exception("Failed to dispatch alert for rule %s", decision.rule_id)
            return False

    async def dispatch_all(
        self,
        decisions: list[RuleDecision],
        raw_text: str,
        message_link: str,
    ) -> list[bool]:
        """Dispatch alerts for all matching decisions."""
        return [
            await self.dispatch(d, raw_text, message_link)
            for d in decisions
            if d.is_match
        ]
