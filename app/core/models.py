"""Domain models for tg-market-watch."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DecisionStatus(str, Enum):  # noqa: UP042 — StrEnum not available on all Python 3.11
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    REJECTED_BY_NEGATIVE = "REJECTED_BY_NEGATIVE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SKIPPED_BY_SCOPE = "SKIPPED_BY_SCOPE"


@dataclass
class EvidenceItem:
    kind: str  # intent, dictionary, numeric, context
    name: str
    value: str | int | float | None = None
    source_text: str | None = None
    normalized_text: str | None = None
    start_token: int | None = None
    end_token: int | None = None
    confidence: float = 1.0


@dataclass
class RawMessage:
    chat_id: int
    message_id: int
    text: str
    chat_title: str | None = None
    sender_id: int | None = None
    message_date: datetime | None = None
    edit_version: int = 0
    chat_username: str | None = None
    is_private_supergroup: bool = False


@dataclass
class NormalizedMessage:
    raw_text: str
    normalized_text: str
    tokens: list[str] = field(default_factory=list)
    canonical_tokens: list[str] = field(default_factory=list)
    ngrams: list[tuple[str, int, int]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    dictionary_matches: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExtractedEntities:
    intents: list[dict[str, Any]] = field(default_factory=list)
    categories: list[dict[str, Any]] = field(default_factory=list)
    numeric: list[dict[str, Any]] = field(default_factory=list)
    models: list[dict[str, Any]] = field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RuleDecision:
    rule_id: str
    status: DecisionStatus
    score: int = 0
    evidence: list[EvidenceItem] = field(default_factory=list)
    negative_evidence: list[EvidenceItem] = field(default_factory=list)
    explanation: str = ""
    config_version: str = ""
    config_hash: str = ""


@dataclass
class MatchRecord:
    message: RawMessage
    normalizer_output: NormalizedMessage
    entities: ExtractedEntities
    decision: RuleDecision
    message_link: str | None = None


@dataclass
class AlertRecord:
    match: MatchRecord
    target_peer: str
    status: str = "pending"  # pending, sent, failed, rate_limited
    telegram_message_id: int | None = None
    error_text: str | None = None
    sent_at: datetime | None = None


@dataclass
class ChatInfo:
    chat_id: int
    title: str | None = None
    username: str | None = None
    enabled: bool = True


@dataclass
class ConfigVersion:
    config_hash: str
    version: int
    loaded_at: datetime | None = None
    rules_count: int = 0
    enabled_rules_count: int = 0
