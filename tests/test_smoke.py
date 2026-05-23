"""Smoke test to verify project imports."""
from __future__ import annotations


def test_imports():
    from app.core.models import (
        AlertRecord,
        ChatInfo,
        ConfigVersion,
        DecisionStatus,
        EvidenceItem,
        ExtractedEntities,
        MatchRecord,
        NormalizedMessage,
        RawMessage,
        RuleDecision,
    )

    assert DecisionStatus.MATCH == "MATCH"
    assert RuleDecision is not None
    assert EvidenceItem is not None
    assert RawMessage is not None
    assert NormalizedMessage is not None
    assert ExtractedEntities is not None
    assert MatchRecord is not None
    assert AlertRecord is not None
    assert ChatInfo is not None
    assert ConfigVersion is not None

    print("Smoke test passed: all domain models import correctly")