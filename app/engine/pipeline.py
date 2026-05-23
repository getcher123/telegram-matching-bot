"""Processing pipeline: message → normalized → extracted → evaluated → stored/alerts."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config.loader import ConfigService
from app.engine.rules import RuleDecision, evaluate_all_rules
from app.extraction.extractor import extract_entities
from app.normalization.pipeline import NormalizationConfig, normalize_text
from app.storage.repository import Repository

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    message_id: int
    chat_id: str
    raw_text: str
    normalized_text: str
    decisions: list[RuleDecision]
    is_duplicate: bool
    match_count: int
    message_link: str = ""


def build_message_link(chat_id: str, message_id: int) -> str:
    """Build Telegram message link."""
    chat_part = chat_id.replace("@", "")
    if chat_part.startswith("-100"):
        chat_part = chat_part[4:]
    return f"https://t.me/c/{chat_part}/{message_id}"


class ProcessingPipeline:
    """Orchestrates the full message processing flow."""

    def __init__(
        self,
        config_svc: ConfigService,
        repository: Repository,
        norm_config: NormalizationConfig | None = None,
    ) -> None:
        self._config_svc = config_svc
        self._repo = repository
        self._norm_config = norm_config or NormalizationConfig()

    async def process_message(
        self,
        message_id: int,
        chat_id: str,
        raw_text: str,
    ) -> PipelineResult:
        """Process a single message through the full pipeline."""
        # 1. Normalize
        normalized = normalize_text(raw_text, self._norm_config)

        # 2. Check dedup
        is_duplicate = await self._repo.is_duplicate(normalized)

        # 3. Get compiled config
        config = self._config_svc.compiled
        if config is None:
            return PipelineResult(
                message_id=message_id,
                chat_id=chat_id,
                raw_text=raw_text,
                normalized_text=normalized,
                decisions=[],
                is_duplicate=is_duplicate,
                match_count=0,
            )

        # 4. Extract entities
        entities = extract_entities(normalized, config.dictionaries)

        # 5. Evaluate rules
        decisions = evaluate_all_rules(entities, config)

        # 6. Store raw message (not a match in dedup sense)
        if not is_duplicate:
            await self._repo.save_raw_message(
                message_id=message_id,
                chat_id=chat_id,
                raw_text=raw_text,
                normalized_text=normalized,
            )

        # 7. Store matches
        matches = [d for d in decisions if d.is_match]
        for decision in matches:
            await self._repo.save_alert_decision(
                message_id=message_id,
                chat_id=chat_id,
                rule_id=decision.rule_id,
                score=decision.score,
                evidence=[
                    (
                        e.to_dict()
                        if hasattr(e, "to_dict")
                        else {"category": e.category, "detail": e.detail}
                    )
                    for e in decision.evidence
                ],
            )

        return PipelineResult(
            message_id=message_id,
            chat_id=chat_id,
            raw_text=raw_text,
            normalized_text=normalized,
            decisions=decisions,
            is_duplicate=is_duplicate,
            match_count=len(matches),
            message_link=build_message_link(chat_id, message_id),
        )
