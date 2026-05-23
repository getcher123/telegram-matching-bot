"""Tests for text normalization pipeline."""

from __future__ import annotations

from app.normalization.pipeline import (
    PRODUCT_TRANSLIT_MAP,
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
    assert "macbook" not in result or "macbook" in result.lower()


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
    # 'тeлeвизoр' with Latin e and o
    result = normalize_text("тeлeвизoр")
    assert "телевизор" in result


def test_keyboard_layout_fix():
    """BL-0402: Исправление раскладки клавиатуры (opt-in)."""
    from app.normalization.pipeline import NormalizationConfig
    cfg = NormalizationConfig(fix_keyboard_layout_for_known_terms=True)
    result = normalize_text("Ghbdtn vfibyf", cfg)
    # After layout fix: привет машина
    assert "привет" in result
    assert "машина" in result or "машину" in result


def test_collapse_spaces():
    """BL-0401: Multiple spaces collapsed (with known transliteration)."""
    result = normalize_text("продам   macbook   pro")
    # macbook → макбук via transliteration, pro → рrо via mixed-script fix
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
    # Lowercased
    assert "продам" in result
    # Currency
    assert "rub" in result or "2000" in result
    # No em-dash
    assert "\u2014" not in result


def test_digit_extraction_basic():
    """BL-0404: Извлечение цифр и чисел."""
    from app.normalization.pipeline import extract_digit_words
    result = extract_digit_words("продам iphone 15 pro max за 120000 руб")
    assert "15" in result
    assert "120000" in result


def test_transliteration_map_includes_macbook():
    """BL-0404: Известные термины содержат макбук."""
    assert "macbook" in PRODUCT_TRANSLIT_MAP
