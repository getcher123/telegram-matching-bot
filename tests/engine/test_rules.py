"""Tests for rule engine."""

from __future__ import annotations

from app.config.compiler import (
    CompiledConfig,
    CompiledNumericConstraint,
    CompiledRule,
)
from app.engine.rules import evaluate_rule, get_matches
from app.extraction.extractor import (
    DictionaryMatch,
    EntityExtractionResult,
    ExtractedNumericSpec,
    Intents,
)


def _make_config(rules=None):
    return CompiledConfig(version=1, config_hash="test123", rules=rules or [])


def _make_tv_rule():
    return CompiledRule(
        id="tv_50_plus_sale",
        title="TV 50+ дюймов",
        enabled=True,
        priority="high",
        threshold=100,
        require_intent_any=frozenset({"sale"}),
        reject_intent_any=frozenset(),
        require_dictionary_any=frozenset({"tv"}),
        require_dictionary_all=frozenset(),
        reject_dictionary_any=frozenset({"accessory"}),
        numeric_constraints=(
            CompiledNumericConstraint(
                entity="diagonal_inches",
                operator=">=",
                value=50.0,
                required=True,
            ),
        ),
        evidence_weights={"sale": 30, "tv": 40, "diagonal_inches": 40},
    )


def _make_entities(
    text: str = "Продам телевизор 55 дюймов",
    specs=None,
    dict_matches=None,
    intents_field=None,
):
    result = EntityExtractionResult(text=text, normalized_text=text, tokens=text.split())
    result.intents = intents_field or Intents(primary="sale", all_intents=["sale"])
    result.numeric_specs = specs or [
        ExtractedNumericSpec(entity="diagonal_inches", value=55.0, unit="inch")
    ]
    result.dictionary_matches = dict_matches or [DictionaryMatch(canonical="tv", term="телевизор")]
    result.has_explicit_price = True
    result.has_specs = True
    return result


def test_tv_rule_pass():
    """BL-0601: Правило TV 50+ проходит с совпадением."""
    rule = _make_tv_rule()
    entities = _make_entities()
    decision = evaluate_rule(rule, entities)
    assert decision.is_match, f"Expected MATCH, got {decision.decision} (score={decision.score})"
    assert decision.score >= 100


def test_tv_rule_no_intent():
    """BL-0601: Правило не проходит без интента sale."""
    rule = _make_tv_rule()
    intents = Intents(primary="", all_intents=["repair"])
    entities = _make_entities(intents_field=intents)
    decision = evaluate_rule(rule, entities)
    assert not decision.is_match


def test_tv_rule_no_tv_dict():
    """BL-0601: Правило не проходит без словаря tv."""
    rule = _make_tv_rule()
    entities = _make_entities(dict_matches=[DictionaryMatch(canonical="macbook", term="macbook")])
    decision = evaluate_rule(rule, entities)
    assert not decision.is_match


def test_tv_rule_small_diagonal():
    """BL-0601: Правило не проходит при диагонали < 50."""
    rule = _make_tv_rule()
    specs = [ExtractedNumericSpec(entity="diagonal_inches", value=32.0, unit="inch")]
    entities = _make_entities(specs=specs)
    decision = evaluate_rule(rule, entities)
    assert not decision.is_match


def test_tv_rule_accessory_reject():
    """BL-0601: Правило отклоняет при accessory."""
    rule = _make_tv_rule()
    entities = _make_entities(dict_matches=[
        DictionaryMatch(canonical="tv", term="телевизор"),
        DictionaryMatch(canonical="accessory", term="чехол"),
    ])
    decision = evaluate_rule(rule, entities)
    assert decision.decision == "REJECTED_BY_NEGATIVE"


def test_disabled_rule_returns_skipped():
    """BL-0601: Отключённое правило = SKIPPED."""
    rule = CompiledRule(id="disabled", title="Disabled", enabled=False, threshold=100)
    entities = _make_entities()
    decision = evaluate_rule(rule, entities)
    assert decision.decision == "SKIPPED"


def test_get_matches_returns_only_matches():
    """BL-0603: get_matches возвращает только MATCH."""
    rules = [_make_tv_rule()]
    config = _make_config(rules)
    entities = _make_entities()
    matches = get_matches(entities, config)
    assert len(matches) >= 1
    assert all(m.is_match for m in matches)


def test_rule_evidence_includes_categories():
    """BL-0608: Evidence содержит категории и веса."""
    rule = _make_tv_rule()
    entities = _make_entities()
    decision = evaluate_rule(rule, entities)
    categories = {e.category for e in decision.evidence}
    assert "intent" in categories
    assert "dictionary" in categories


def test_rule_with_no_constraints():
    """BL-0601: Правило без ограничений оценивается по score."""
    rule = CompiledRule(
        id="simple", title="Simple", enabled=True, threshold=30,
        require_intent_any=frozenset({"sale"}),
        evidence_weights={"sale": 40},
    )
    entities = _make_entities()
    decision = evaluate_rule(rule, entities)
    assert decision.score >= 30
    assert decision.is_match
