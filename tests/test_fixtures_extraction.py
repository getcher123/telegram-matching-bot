"""Parameterized entity extraction tests using fixture YAML."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.extraction.extractor import extract_entities
from app.normalization.pipeline import NormalizationConfig, normalize_text

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "extraction"

with open(FIXTURES_DIR / "entity_cases.yaml") as f:
    ENT_CASES = yaml.safe_load(f)["cases"]

cfg = NormalizationConfig()


def normalize_for_test(text: str) -> str:
    """Run normalization with defaults."""
    return normalize_text(text, cfg)


@pytest.mark.parametrize("case", ENT_CASES, ids=lambda c: c["id"])
def test_entity_extraction(case: dict) -> None:
    """Test entity extraction against fixture case."""
    norm = normalize_for_test(case["text"])
    result = extract_entities(norm)

    exp = case["expected"]

    # Intent
    exp_intent = exp.get("intent", "")
    if exp_intent:
        assert result.intents.primary == exp_intent, (
            f"{case['id']}: expected intent={exp_intent!r}, got {result.intents.primary!r}"
        )

    # Price
    exp_price = exp.get("price")
    if exp_price:
        assert result.has_explicit_price, f"{case['id']}: expected price, but none found"
        # Check any price matches expected amount/currency
        found = False
        for p in result.prices:
            if (
                abs(p.value - exp_price["amount"]) < 1
                and p.currency == exp_price["currency"]
            ):
                found = True
                break
        assert found, (
            f"{case['id']}: expected price {exp_price}, "
            f"got prices={[(p.value, p.currency) for p in result.prices]}"
        )
    else:
        # If no price expected and none found, that's fine
        pass

    # Negatives (reject intents)
    exp_negatives = exp.get("negatives", None)
    if exp_negatives is not None:
        for neg in exp_negatives:
            assert neg in result.intents.reject_intents, (
                f"{case['id']}: expected negative '{neg}' in {result.intents.reject_intents}"
            )

    # Diagonal inches (from numeric_specs)
    exp_diag = exp.get("diagonal_inches")
    if exp_diag is not None:
        found_diag = False
        for spec in result.numeric_specs:
            if spec.entity == "diagonal_inches" and abs(spec.value - exp_diag) < 0.01:
                found_diag = True
                break
        assert found_diag, (
            f"{case['id']}: expected diagonal_inches={exp_diag}, "
            f"got numeric_specs={[(s.entity, s.value) for s in result.numeric_specs]}"
        )
