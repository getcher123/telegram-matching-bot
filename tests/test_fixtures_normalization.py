"""Parameterized normalization tests using fixture YAML."""

from __future__ import annotations

import pytest

from app.normalization.pipeline import NormalizationConfig, normalize_text, tokenize
from tests.conftest import load_yaml_cases

NORM_CASES = load_yaml_cases("normalization/normalization_cases.yaml")
CONF_CASES = load_yaml_cases("normalization/confusable_cases.yaml")


class TestNormalizationFixtures:
    """NORM-* cases: parameterized normalization tests."""

    @pytest.mark.parametrize("case", NORM_CASES, ids=lambda c: c["id"])
    def test_normalization(self, case: dict) -> None:
        cfg = NormalizationConfig()
        result = normalize_text(case["input"], cfg)
        tokens = tokenize(result)

        expected_text = case["expected_text"]
        expected_tokens = case["expected_tokens"]

        assert result == expected_text, (
            f"{case['id']}: expected text {expected_text!r}, got {result!r}"
        )
        assert tokens == expected_tokens, (
            f"{case['id']}: expected tokens {expected_tokens}, got {tokens}"
        )


class TestConfusableFixtures:
    """CONF-* cases: confusable Cyrillic/Latin normalization."""

    @pytest.mark.parametrize("case", CONF_CASES, ids=lambda c: c["id"])
    def test_confusable(self, case: dict) -> None:
        cfg = NormalizationConfig()
        result = normalize_text(case["input"], cfg)
        tokens = tokenize(result)

        expected_text = case["expected_text"]
        assert result == expected_text, (
            f"{case['id']}: expected {expected_text!r}, got {result!r}"
        )

        if "expected_canonical_tokens" in case:
            assert tokens == case["expected_canonical_tokens"], (
                f"{case['id']}: expected tokens {case['expected_canonical_tokens']}, got {tokens}"
            )
