"""Parameterized rule engine tests using fixture YAML.

Tests the full pipeline: text → normalization → extraction → rule evaluation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.config.compiler import (
    CompiledConfig,
    CompiledNumericConstraint,
    CompiledRule,
)
from app.engine.rules import evaluate_rule
from app.extraction.extractor import extract_entities
from app.normalization.pipeline import NormalizationConfig, normalize_text

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "rules"

with open(FIXTURES_DIR / "message_decision_cases.yaml") as f:
    MSG_CASES = yaml.safe_load(f)["cases"]

cfg = NormalizationConfig()


def _make_rule(raw: dict) -> CompiledRule:
    """Convert a raw fixture-style rule dict to CompiledRule."""
    require = raw.get("require", {})
    reject = raw.get("reject_if", {})

    require_intents = []
    if isinstance(require.get("intent"), str):
        require_intents = [require["intent"]]
    elif isinstance(require.get("intent"), list):
        require_intents = require["intent"]

    reject_intents = []
    if isinstance(reject.get("intents"), list):
        reject_intents = reject["intents"]
    if reject.get("fake"):
        reject_intents.append("fake")
    if reject.get("accessory_only"):
        reject_intents.append("accessory")
    if reject.get("part_only"):
        reject_intents.append("part_only")

    num_constraints = []
    op_map = {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<", "eq": "=="}
    if isinstance(require.get("diagonal_inches"), dict):
        for op, val in require["diagonal_inches"].items():
            normalized_op = op_map.get(op, op)
            num_constraints.append(
                CompiledNumericConstraint(
                    entity="diagonal_inches",
                    operator=normalized_op,
                    value=float(val),
                    required=True,
                )
            )

    return CompiledRule(
        id=raw["id"],
        title=raw.get("title", ""),
        enabled=raw.get("enabled", True),
        threshold=30,
        require_intent_any=frozenset(require_intents),
        reject_intent_any=frozenset(reject_intents),
        numeric_constraints=tuple(num_constraints),
    )


# Build the compiled config from the fixture YAML
FIXTURE_CONFIG_PATH = (
    Path(__file__).parent / "fixtures" / "config" / "watch_config.valid.yaml"
)
with open(FIXTURE_CONFIG_PATH) as f:
    RAW_CONFIG = yaml.safe_load(f)

COMPILED_RULES = tuple(_make_rule(r) for r in RAW_CONFIG.get("rules", []))
COMPILED_CONFIG = CompiledConfig(
    version=1,
    config_hash="test-hash",
    rules=COMPILED_RULES,
    dictionaries=(),
)


def _rule_by_id(rule_id: str) -> CompiledRule:
    """Find a compiled rule by ID."""
    for r in COMPILED_RULES:
        if r.id == rule_id:
            return r
    raise KeyError(f"Rule {rule_id} not found in compiled config")


@pytest.mark.parametrize("case", MSG_CASES, ids=lambda c: c["id"])
def test_message_decision(case: dict) -> None:
    """Test end-to-end rule evaluation against message fixture."""
    exp = case["expected"]
    rule_id = exp.get("rule_id", "")
    rule = _rule_by_id(rule_id)

    # Normalize
    normalized = normalize_text(case["text"], cfg)

    # Extract entities (no dictionaries for test)
    entities = extract_entities(normalized, dictionaries=())

    # Evaluate
    decision = evaluate_rule(rule, entities, COMPILED_CONFIG)

    # Check status
    exp_status = exp.get("status", "NO_MATCH")
    assert decision.decision == exp_status, (
        f"{case['id']}: expected status={exp_status}, "
        f"got {decision.decision!r} (score={decision.score})\n"
        f"  Text: {case['text']!r}\n"
        f"  Normalized: {normalized!r}\n"
        f"  Intents: {entities.intents}\n"
        f"  Reject intents: {entities.intents.reject_intents}\n"
        f"  Prices: {[(p.value, p.currency) for p in entities.prices]}\n"
        f"  Specs: {[(s.entity, s.value) for s in entities.numeric_specs]}"
    )

    # Check reject_reason from evidence
    exp_reason = exp.get("reject_reason")
    if exp_reason:
        # Convert evidence to reason string
        evidence_details = "; ".join(
            f"{e.category}: {e.detail}" for e in decision.evidence
        )
        # Check that the reject reason appears in the decision
        assert exp_reason in evidence_details, (
            f"{case['id']}: expected reason '{exp_reason}' not found in evidence: "
            f"{evidence_details}"
        )

    # Check minimum evidence
    min_ev = exp.get("minimum_evidence", {})
    if min_ev:
        if "intent" in min_ev:
            assert min_ev["intent"] in entities.intents.all_intents, (
                f"{case['id']}: expected intent '{min_ev['intent']}' "
                f"not in {entities.intents.all_intents}"
            )
        if "diagonal_inches" in min_ev:
            found = any(
                s.entity == "diagonal_inches"
                and abs(s.value - min_ev["diagonal_inches"]) < 0.01
                for s in entities.numeric_specs
            )
            assert found, (
                f"{case['id']}: expected diagonal {min_ev['diagonal_inches']} "
                f"not found in specs: {[(s.entity, s.value) for s in entities.numeric_specs]}"
            )
        if "price" in min_ev:
            exp_price = min_ev["price"]
            found = any(
                abs(p.value - exp_price["amount"]) < 1
                and p.currency == exp_price["currency"]
                for p in entities.prices
            )
            assert found, (
                f"{case['id']}: expected price {exp_price} "
                f"not in {[(p.value, p.currency) for p in entities.prices]}"
            )
