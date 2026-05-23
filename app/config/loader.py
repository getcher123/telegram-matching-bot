"""YAML config loader with atomic reload."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from app.config.compiler import (
    CompiledConfig,
    CompiledDictionary,
    CompiledNumericConstraint,
    CompiledRule,
)
from app.config.hashing import compute_config_hash
from app.config.models import RootConfig

logger = logging.getLogger(__name__)


def _compile_dictionaries(raw: dict[str, list[dict[str, Any]]]) -> tuple[CompiledDictionary, ...]:
    """Compile dictionary groups from raw YAML data."""
    compiled: list[CompiledDictionary] = []
    for group_name, groups in raw.items():
        for group in groups:
            canonical = group.get("canonical", group_name)
            terms = group.get("terms", [])
            multi_token_terms: set[tuple[str, ...]] = set()
            single_terms: set[str] = set()
            for term in terms:
                tokens = tuple(term.lower().split())
                if len(tokens) > 1:
                    multi_token_terms.add(tokens)
                else:
                    single_terms.add(tokens[0])
            compiled.append(
                CompiledDictionary(
                    canonical=canonical,
                    terms=frozenset(single_terms),
                    multi_token_terms=frozenset(multi_token_terms),
                )
            )
    return tuple(compiled)


def _compile_rule(raw: dict[str, Any]) -> CompiledRule:
    """Compile a single rule from raw YAML data."""
    constraints = raw.get("numeric_constraints") or []
    compiled_constraints = tuple(
        CompiledNumericConstraint(
            entity=c.get("entity", ""),
            operator=c.get("operator", ">="),
            value=float(c.get("value", 0)),
            required=c.get("required", True),
            context_dictionary_any=frozenset(c.get("context_dictionary_any") or []),
            context_window_tokens=c.get("context_window_tokens"),
        )
        for c in constraints
    )

    return CompiledRule(
        id=raw["id"],
        title=raw.get("title", ""),
        enabled=raw.get("enabled", True),
        priority=raw.get("priority", "medium"),
        threshold=raw.get("threshold", 100),
        require_intent_any=frozenset(raw.get("require_intent_any") or []),
        reject_intent_any=frozenset(raw.get("reject_intent_any") or []),
        require_dictionary_any=frozenset(raw.get("require_dictionary_any") or []),
        require_dictionary_all=frozenset(raw.get("require_dictionary_all") or []),
        reject_dictionary_any=frozenset(raw.get("reject_dictionary_any") or []),
        numeric_constraints=compiled_constraints,
        evidence_weights=raw.get("evidence_weights") or {},
        alert_template_id=raw.get("alert_template_id", "default_market_match"),
    )


class ConfigService:
    """Manages YAML config loading, validation, compilation and atomic reload."""

    def __init__(self, config_path: str = "config/watch.yaml") -> None:
        self._path = Path(config_path)
        self._active: CompiledConfig | None = None
        self._raw: RootConfig | None = None
        self._raw_yaml: str = ""

    @property
    def active(self) -> CompiledConfig | None:
        return self._active

    @property
    def raw(self) -> RootConfig | None:
        return self._raw

    def load_initial(self) -> CompiledConfig:
        """Load and compile config on startup. Raises on failure."""
        return self._load()

    def reload(self) -> CompiledConfig | None:
        """Try to reload config. Returns new CompiledConfig or None on failure (keeps old)."""
        try:
            new_config = self._load()
            logger.info(
                "Config reloaded: hash=%s rules=%d", new_config.config_hash, len(new_config.rules)
            )
            return new_config
        except Exception:
            logger.exception("Config reload failed, keeping active config")
            return None

    def _load(self) -> CompiledConfig:
        """Internal: read, validate, compile config."""
        raw_yaml = self._read_file()
        config_hash = compute_config_hash(raw_yaml)
        data = yaml.safe_load(raw_yaml)

        if not isinstance(data, dict):
            raise ValueError("YAML root must be a mapping")

        validated = RootConfig.model_validate(data)

        compiled_rules = tuple(_compile_rule(r.model_dump()) for r in validated.rules)
        compiled_dicts = _compile_dictionaries(
            {k: [g.model_dump() for g in v] for k, v in validated.dictionaries.items()}
        )

        compiled = CompiledConfig(
            version=validated.version,
            config_hash=config_hash,
            rules=compiled_rules,
            dictionaries=compiled_dicts,
            telemetry={
                "rules_count": len(compiled_rules),
                "enabled_rules": sum(1 for r in compiled_rules if r.enabled),
            },
        )

        self._active = compiled
        self._raw = validated
        self._raw_yaml = raw_yaml
        return compiled

    def _read_file(self) -> str:
        if not self._path.exists():
            raise FileNotFoundError(f"Config not found: {self._path}")
        return self._path.read_text(encoding="utf-8")
