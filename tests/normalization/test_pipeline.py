"""Tests for text normalization pipeline."""

from __future__ import annotations

from app.normalization.pipeline import (
    KNOWN_LATIN_TOKENS,
    extract_digit_words,
    is_latin_heavy,
    levenshtein_distance,
    normalize_text,
    tokenize,
)


def test_nfkc_normalization():
    """BL-0401: Unicode NFKC (full-width → half-width)."""
    result = normalize_text("Ｐｒｏｄｕｃｔ")
    assert "product" in result


def test_lowercase():
    """BL-0401: Lowercase."""
    result = normalize_text("Продам MacBook Pro")
    assert "продам" in result


def test_yo_to_e():
    """BL-0401: ё → е."""
    result = normalize_text("продаётся")
    assert "продается" in result
    assert "ё" not in result


def test_zero_width_removal():
    """BL-0401: Zero-width chars removed."""
    result = normalize_text("pro\u200bduct")
    assert "product" in result


def test_quote_normalization():
    """BL-0401: Quotes normalized."""
    result = normalize_text("\u201cпродам\u201d")
    assert '"продам"' in result


def test_dash_normalization():
    """BL-0401: Dashes normalized."""
    result = normalize_text("mac\u2014book")
    assert "mac-book" in result


def test_currency_normalization():
    """BL-0401: Currency symbols spaced."""
    result = normalize_text("цена 100\u20bd")
    assert "rub" in result


def test_mixed_cyrillic_latin():
    """BL-0402: Исправление смешанной кириллицы/латиницы."""
    result = normalize_text("тeлeвизoр")
    assert "телевизор" in result


def test_collapse_spaces():
    """BL-0401: Multiple spaces collapsed."""
    result = normalize_text("продам   macbook   pro")
    assert "продам" in result
    assert "  " not in result


def test_tokenize_basic():
    """BL-0405: Токенизация."""
    tokens = tokenize("продам macbook pro 2023")
    assert tokens == ["продам", "macbook", "pro", "2023"]


def test_levenshtein():
    """BL-0404: Расстояние Левенштейна."""
    assert levenshtein_distance("macbook", "macbook") == 0
    assert levenshtein_distance("macbook", "macbuk") == 2
    assert levenshtein_distance("telefon", "telephone") == 3


def test_is_latin_heavy_latin():
    """BL-0402: Детекция латинского текста."""
    assert is_latin_heavy("ghbdtn vfibyf")


def test_is_latin_heavy_cyrillic():
    """BL-0402: Детекция кириллицы."""
    assert not is_latin_heavy("привет машина")


def test_normalize_full_pipeline_example():
    """Integration: полный пайплайн на примере."""
    raw = "Продам MacBook Pro M4 Pro 14 дюймов, цена 2000\u20bd"
    result = normalize_text(raw)
    assert "продам" in result
    assert "rub" in result or "2000" in result
    assert "\u2014" not in result


def test_digit_extraction_basic():
    """BL-0404: Извлечение цифр и чисел."""
    result = extract_digit_words("продам iphone 15 pro max за 120000 руб")
    assert "15" in result
    assert "120000" in result


def test_known_latin_tokens_has_macbook():
    """Known tokens include macbook."""
    assert "macbook" in KNOWN_LATIN_TOKENS
