"""Tests for processing pipeline, dedup, and alert dispatcher."""

from __future__ import annotations

from app.alerts.dispatcher import AlertDispatcher
from app.engine.dedup import DedupService
from app.engine.rules import RuleDecision


def test_dedup_hash():
    """BL-0703: Хеш нормализованного текста стабилен."""
    svc = DedupService.__new__(DedupService)
    h1 = svc.hash_normalized("  Продам MacBook   ")
    h2 = svc.hash_normalized("продам macbook")
    assert h1 == h2
    assert len(h1) == 64


def test_dedup_hash_different():
    """BL-0703: Разные тексты дают разные хеши."""
    svc = DedupService.__new__(DedupService)
    h1 = svc.hash_normalized("Продам телевизор")
    h2 = svc.hash_normalized("Продам macbook")
    assert h1 != h2


def test_alert_format_default():
    """BL-0801: Форматирование алерта по шаблону."""
    dispatcher = AlertDispatcher()
    decision = RuleDecision(
        rule_id="tv_50_plus",
        rule_title="TV 50+ дюймов",
        decision="MATCH",
        score=110.0,
        threshold=100,
    )
    text = dispatcher.format_alert(
        decision=decision,
        raw_text="Продам телевизор 55 дюймов",
        message_link="https://t.me/c/12345/678",
    )
    assert "⚡" in text
    assert "TV 50+" in text
    assert "110" in text
    assert "100" in text


def test_alert_format_short():
    """BL-0801: Короткий шаблон."""
    dispatcher = AlertDispatcher()
    decision = RuleDecision(
        rule_id="test", rule_title="Test", decision="MATCH", score=50, threshold=100
    )
    text = dispatcher.format_alert(
        decision, "Короткое сообщение", "https://t.me/c/1/2", "short_match"
    )
    assert "⚡" in text
    assert "Короткое" in text


def test_build_message_link():
    """BL-0901: Формирование ссылки на сообщение."""
    from app.engine.pipeline import build_message_link

    link = build_message_link("@test_group", 123)
    assert link == "https://t.me/c/test_group/123"

    link2 = build_message_link("-1001234567890", 42)
    assert "1234567890" in link2
    assert "/42" in link2
