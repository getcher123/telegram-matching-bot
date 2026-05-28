"""Rule engine — evaluates rules against extracted entities.

Deterministic, evidence-based decision making.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config.compiler import CompiledConfig, CompiledRule
from app.extraction.extractor import EntityExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    category: str
    detail: str
    weight: int = 0
    confidence: float = 1.0


@dataclass
class RuleDecision:
    rule_id: str
    rule_title: str
    decision: str
    score: float = 0.0
    threshold: int = 100
    evidence: list[EvidenceItem] = field(default_factory=list)
    config_hash: str = ""

    @property
    def is_match(self) -> bool:
        return self.decision == "MATCH"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "decision": self.decision,
            "score": self.score,
            "threshold": self.threshold,
            "evidence": [
                {"category": e.category, "detail": e.detail, "weight": e.weight}
                for e in self.evidence
            ],
            "config_hash": self.config_hash,
        }


def evaluate_rule(
    rule: CompiledRule,
    entities: EntityExtractionResult,
    config: CompiledConfig | None = None,
) -> RuleDecision:
    """Evaluate a single rule against extracted entities."""
    config_hash = config.config_hash if config else ""
    decision = RuleDecision(
        rule_id=rule.id,
        rule_title=rule.title,
        decision="NO_MATCH",
        config_hash=config_hash,
    )

    # 1. Skip disabled rules
    if not rule.enabled:
        decision.decision = "SKIPPED"
        return decision

    # 2. Global reject intents
    if config and config.telemetry:
        global_rejects = config.telemetry.get("global_reject_if_any_intent", [])
        for intent in entities.intents.all_intents:
            if intent in global_rejects:
                decision.decision = "REJECTED_BY_NEGATIVE"
                decision.evidence.append(
                    EvidenceItem(
                        category="global_reject",
                        detail=f"Global reject intent: {intent}",
                        weight=0,
                    )
                )
                return decision

    # 3. reject_intent_any — check BEFORE require so buy/repair/etc is caught first
    if rule.reject_intent_any:
        all_ints = set(entities.intents.all_intents + entities.intents.reject_intents)
        matched = all_ints & rule.reject_intent_any
        if matched:
            decision.decision = "REJECTED_BY_NEGATIVE"
            for intent in matched:
                decision.evidence.append(
                    EvidenceItem(
                        category="reject_intent",
                        detail=f"Reject: {intent}",
                        weight=0,
                    )
                )
            return decision

    # 4. require_intent_any
    if rule.require_intent_any:
        matched = set(entities.intents.all_intents) & rule.require_intent_any
        if not matched:
            decision.evidence.append(
                EvidenceItem(
                    category="intent",
                    detail=(
                            f"Required intent not found "
                            f"(need: {', '.join(rule.require_intent_any)})"
                        ),
                    weight=0,
                )
            )
            decision.decision = "NO_MATCH"
            decision.score = 0.0
            return decision
        for intent in matched:
            decision.evidence.append(
                EvidenceItem(category="intent", detail=f"Intent: {intent}", weight=30)
            )

    # 5. require_dictionary_any
    if rule.require_dictionary_any:
        matched_canonicals = {m.canonical for m in entities.dictionary_matches}
        matched = matched_canonicals & rule.require_dictionary_any
        if not matched:
            decision.evidence.append(
                EvidenceItem(
                    category="dictionary",
                    detail=f"No dictionary term (need: {', '.join(rule.require_dictionary_any)})",
                    weight=0,
                )
            )
            decision.decision = "NO_MATCH"
            decision.score = 0.0
            return decision
        for canon in matched:
            w = rule.evidence_weights.get(canon, 30)
            decision.evidence.append(
                EvidenceItem(category="dictionary", detail=f"Dict: {canon}", weight=w)
            )

    # 6. require_dictionary_all
    if rule.require_dictionary_all:
        matched_canonicals = {m.canonical for m in entities.dictionary_matches}
        missing = rule.require_dictionary_all - matched_canonicals
        if missing:
            decision.evidence.append(
                EvidenceItem(
                    category="dictionary",
                    detail=f"Missing dict: {', '.join(missing)}",
                    weight=0,
                )
            )
            decision.decision = "NO_MATCH"
            decision.score = 0.0
            return decision
        for canon in rule.require_dictionary_all:
            w = rule.evidence_weights.get(canon, 30)
            decision.evidence.append(
                EvidenceItem(category="dictionary", detail=f"All dict: {canon}", weight=w)
            )

    # 7. reject_dictionary_any
    if rule.reject_dictionary_any:
        matched_canonicals = {m.canonical for m in entities.dictionary_matches}
        matched = matched_canonicals & rule.reject_dictionary_any
        if matched:
            decision.decision = "REJECTED_BY_NEGATIVE"
            for canon in matched:
                decision.evidence.append(
                    EvidenceItem(
                        category="reject_dictionary",
                        detail=f"Reject dict: {canon}",
                        weight=0,
                    )
                )
            return decision

    # 8. Numeric constraints
    if rule.numeric_constraints:
        passed = True
        for constraint in rule.numeric_constraints:
            result = _evaluate_numeric_constraint(constraint, entities)
            if result is None:
                decision.evidence.append(
                    EvidenceItem(
                        category=constraint.entity,
                        detail=(
                            f"Num OK: {constraint.entity} "
                            f"{constraint.operator} {constraint.value}"
                        ),
                        weight=rule.evidence_weights.get(constraint.entity, 40),
                    )
                )
            else:
                decision.evidence.append(result)
                if constraint.required and (
                    "failed" in result.detail.lower()
                    or "not found" in result.detail.lower()
                ):
                    passed = False
        if not passed:
            decision.decision = "NO_MATCH"
            decision.score = 0.0
            return decision

    # 9. Score
    score = sum(e.weight for e in decision.evidence)
    decision.score = float(score)

    # 10. Threshold
    if score >= rule.threshold:
        decision.decision = "MATCH"
    else:
        decision.decision = "NO_MATCH"

    return decision


def _is_bare_number(raw: str) -> bool:
    """Check if a numeric spec is a bare number (no unit suffix)."""
    unit_indicators = ["дюйм", "inch", "\"", '"', "in"]
    raw_lower = raw.lower()
    for indicator in unit_indicators:
        if indicator in raw_lower:
            return False
    return True


def _find_context_bare_number(
    constraint: Any,
    entities: EntityExtractionResult,
) -> int | None:
    """Find a bare number matching constraint within context window of a dictionary term."""
    if not constraint.context_dictionary_any or not constraint.context_window_tokens:
        return None

    # Which context dictionary terms were matched in this message?
    matched_canonicals = {
        dm.canonical
        for dm in entities.dictionary_matches
        if dm.canonical in constraint.context_dictionary_any
    }
    if not matched_canonicals:
        return None

    # Find token positions of matched dictionary terms
    context_positions: set[int] = set()
    for i, tok in enumerate(entities.tokens):
        for dm in entities.dictionary_matches:
            if dm.canonical in matched_canonicals and tok == dm.term:
                context_positions.add(i)

    # Scan tokens for bare numbers near context positions
    window = constraint.context_window_tokens
    for i, tok in enumerate(entities.tokens):
        try:
            value = float(tok.replace(",", "."))
            if value < 10 or value > 200:  # plausible diagonal range
                continue
            # Check if within context window of a matched dictionary term
            for pos in context_positions:
                if abs(i - pos) <= window:
                    # Verify operator
                    ok = False
                    if constraint.operator == ">=":
                        ok = value >= constraint.value
                    elif constraint.operator == "<=":
                        ok = value <= constraint.value
                    elif constraint.operator == "==":
                        ok = abs(value - constraint.value) < 0.01
                    elif constraint.operator == ">":
                        ok = value > constraint.value
                    elif constraint.operator == "<":
                        ok = value < constraint.value
                    if ok:
                        return int(value)
        except ValueError:
            continue

    return None


def _evaluate_numeric_constraint(
    constraint: Any,
    entities: EntityExtractionResult,
) -> EvidenceItem | None:
    """Evaluate numeric constraint. Returns None on success."""
    relevant_specs = [s for s in entities.numeric_specs if s.entity == constraint.entity]

    # First pass: check unit-backed specs (дюймов, inch, etc.)
    for spec in relevant_specs:
        if not _is_bare_number(spec.raw):
            value = spec.value
            ok = False
            if constraint.operator in (">=", "<=", "==", ">", "<"):
                match constraint.operator:
                    case ">=":
                        ok = value >= constraint.value
                    case "<=":
                        ok = value <= constraint.value
                    case "==":
                        ok = abs(value - constraint.value) < 0.01
                    case ">":
                        ok = value > constraint.value
                    case "<":
                        ok = value < constraint.value
            if ok:
                return None
            return EvidenceItem(
                category=constraint.entity,
                detail=f"Numeric failed: {value} {constraint.operator} {constraint.value}",
                weight=0,
            )

    # Second pass: context-aware bare number (no unit)
    if constraint.context_dictionary_any and constraint.context_window_tokens:
        bare_value = _find_context_bare_number(constraint, entities)
        if bare_value is not None:
            return None
        return EvidenceItem(
            category=constraint.entity,
            detail=f"Numeric failed: bare {constraint.entity} not found near {', '.join(constraint.context_dictionary_any)}",
            weight=0,
        )

    # No constraints found at all
    return EvidenceItem(
        category=constraint.entity,
        detail=f"Numeric failed: {constraint.entity} not found",
        weight=0,
    )


def evaluate_all_rules(
    entities: EntityExtractionResult,
    config: CompiledConfig,
) -> list[RuleDecision]:
    """Evaluate all enabled rules against extracted entities."""
    decisions = [evaluate_rule(rule, entities, config) for rule in config.rules]
    decisions.sort(key=lambda d: d.score, reverse=True)
    return decisions


def get_matches(
    entities: EntityExtractionResult,
    config: CompiledConfig,
) -> list[RuleDecision]:
    """Get only matching decisions."""
    return [d for d in evaluate_all_rules(entities, config) if d.is_match]
