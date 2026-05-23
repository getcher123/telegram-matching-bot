"""Compiled configuration ready for rule engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompiledDictionary:
    """Immutable compiled dictionary for matching."""

    canonical: str
    terms: frozenset[str]
    multi_token_terms: frozenset[tuple[str, ...]]
    min_token_length: int = 5


@dataclass(frozen=True)
class CompiledNumericConstraint:
    entity: str
    operator: str
    value: float
    required: bool
    context_dictionary_any: frozenset[str] | None = None
    context_window_tokens: int | None = None


@dataclass(frozen=True)
class CompiledRule:
    """Immutable compiled rule ready for matching."""

    id: str
    title: str
    enabled: bool
    priority: str
    threshold: int
    require_intent_any: frozenset[str] = field(default_factory=frozenset)
    reject_intent_any: frozenset[str] = field(default_factory=frozenset)
    require_dictionary_any: frozenset[str] = field(default_factory=frozenset)
    require_dictionary_all: frozenset[str] = field(default_factory=frozenset)
    reject_dictionary_any: frozenset[str] = field(default_factory=frozenset)
    numeric_constraints: tuple[CompiledNumericConstraint, ...] = field(default_factory=tuple)
    evidence_weights: dict[str, int] = field(default_factory=dict)
    alert_template_id: str = "default_market_match"


@dataclass(frozen=True)
class CompiledConfig:
    """Fully compiled, immutable configuration ready for runtime."""

    version: int
    config_hash: str
    rules: tuple[CompiledRule, ...] = field(default_factory=tuple)
    dictionaries: tuple[CompiledDictionary, ...] = field(default_factory=tuple)
    telemetry: dict = field(default_factory=dict)

    @property
    def enabled_rules(self) -> tuple[CompiledRule, ...]:
        return tuple(r for r in self.rules if r.enabled)
