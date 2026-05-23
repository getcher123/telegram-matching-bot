"""Tests for entity extraction."""

from __future__ import annotations

from app.config.compiler import CompiledDictionary
from app.extraction.extractor import (
    EntityExtractionResult,
    extract_entities,
    extract_intents,
    extract_numeric_specs,
    extract_price,
    match_dictionaries,
)

# ── Price extraction ────────────────────────────────────────────


def test_extract_price_explicit_rub():
    """BL-0501: Извлечение явной цены в рублях."""
    prices = extract_price("Продам за 120000 руб")
    assert len(prices) >= 1
    assert any(p.value == 120000.0 for p in prices)


def test_extract_price_with_rub_char():
    """BL-0501: Цена с символом р."""
    prices = extract_price("цена 50000р")
    assert len(prices) >= 1
    assert any(p.value == 50000.0 for p in prices)


def test_extract_price_usd():
    """BL-0501: Цена в долларах."""
    prices = extract_price("MacBook $2500")
    assert len(prices) >= 1
    assert any(p.value == 2500.0 for p in prices)


def test_extract_price_word_based():
    """BL-0501: Цена по ключевому слову 'цена'."""
    prices = extract_price("цена 120000")
    assert len(prices) >= 1
    assert any(p.value == 120000.0 for p in prices)


def test_extract_price_no_false_positive():
    """BL-0501: Не извлекать ложно цены из номеров моделей."""
    prices = extract_price("MacBook Pro M4 Pro 14 дюймов")
    # 14 is not a price, M4 is not a price
    price_values = [p.value for p in prices]
    assert 14.0 not in price_values
    assert 4.0 not in price_values


# ── Numeric spec extraction ────────────────────────────────────


def test_extract_diagonal():
    """BL-0502: Извлечение диагонали."""
    specs = extract_numeric_specs("телевизор 55 дюймов")
    diagonals = [s for s in specs if "diagonal" in s.entity]
    assert len(diagonals) >= 1
    assert any(s.value == 55.0 for s in diagonals)


def test_extract_diagonal_with_quotes():
    """BL-0502: Диагональ в дюймах с кавычками."""
    specs = extract_numeric_specs("телевизор 65\"")
    diagonals = [s for s in specs if "diagonal" in s.entity]
    assert len(diagonals) >= 1
    assert any(s.value == 65.0 for s in diagonals)


def test_extract_storage():
    """BL-0502: Извлечение объёма хранилища."""
    specs = extract_numeric_specs("MacBook 512 гб")
    storage = [s for s in specs if "storage" in s.entity]
    assert len(storage) >= 1
    assert any(s.value == 512.0 for s in storage)


# ── Intent extraction ──────────────────────────────────────────


def test_intent_sale():
    """BL-0503: Распознавание интента 'продажа'."""
    tokens = ["продам", "macbook", "pro"]
    intents = extract_intents(tokens)
    assert "sale" in intents.all_intents
    assert intents.primary == "sale"


def test_intent_buy():
    """BL-0503: Распознавание интента 'покупка'."""
    tokens = ["куплю", "macbook"]
    intents = extract_intents(tokens)
    assert "buy" in intents.all_intents
    assert intents.primary == "buy"


def test_intent_fake_rejection():
    """BL-0503: Распознавание реджект-интента 'fake'."""
    tokens = ["airpods", "реплика"]
    intents = extract_intents(tokens)
    assert "fake" in intents.reject_intents


def test_intent_no_false_positive():
    """BL-0503: Не помечать обычные слова как интенты."""
    tokens = ["продам", "телевизор", "хороший"]
    intents = extract_intents(tokens)
    assert "sale" in intents.all_intents
    assert "repair" not in intents.all_intents


# ── Dictionary matching ────────────────────────────────────────


def test_dict_match_exact():
    """BL-0504: Точное совпадение словаря."""
    dicts = (
        CompiledDictionary(
            canonical="tv",
            terms=frozenset({"телевизор", "тв"}),
            multi_token_terms=frozenset(),
        ),
    )
    matches = match_dictionaries(["продам", "телевизор", "55", "дюймов"], dicts)
    tv_matches = [m for m in matches if m.canonical == "tv"]
    assert len(tv_matches) >= 1
    assert tv_matches[0].term == "телевизор"


def test_dict_match_multi_token():
    """BL-0504: Многословное совпадение."""
    dicts = (
        CompiledDictionary(
            canonical="sale",
            terms=frozenset(),
            multi_token_terms=frozenset({("в", "наличии")}),
        ),
    )
    matches = match_dictionaries(["товар", "в", "наличии"], dicts)
    sale_matches = [m for m in matches if m.canonical == "sale"]
    assert len(sale_matches) >= 1


# ── Full extraction ────────────────────────────────────────────


def test_full_extraction():
    """BL-0505: Полное извлечение сущностей."""
    dicts = (
        CompiledDictionary(
            canonical="macbook",
            terms=frozenset({"macbook", "макбук"}),
            multi_token_terms=frozenset({("macbook", "pro")}),
        ),
    )
    result = extract_entities("Продам MacBook Pro M4 Pro за 200000 руб", dicts)
    assert isinstance(result, EntityExtractionResult)
    assert "sale" in result.intents.all_intents
    assert len(result.prices) >= 1
    assert any(m.canonical == "macbook" for m in result.dictionary_matches)


def test_empty_text():
    """Пустой текст не вызывает ошибок."""
    result = extract_entities("", ())
    assert result.tokens == []
    assert result.intents.primary == ""
    assert len(result.prices) == 0
