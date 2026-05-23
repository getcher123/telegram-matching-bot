"""Entity extraction from normalized text.

Extracts: price, numeric specs, intent, dictionary matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config.compiler import CompiledDictionary
from app.normalization.pipeline import levenshtein_distance

# ── Data classes ────────────────────────────────────────────────────


@dataclass
class ExtractedPrice:
    value: float
    currency: str = "rub"
    raw: str = ""
    source: str = ""  # explicit / per_word


@dataclass
class ExtractedNumericSpec:
    entity: str
    value: float
    unit: str = ""
    raw: str = ""


@dataclass
class DictionaryMatch:
    canonical: str
    term: str
    confidence: float = 1.0  # 0.0–1.0 for fuzzy matches


@dataclass
class Intents:
    primary: str = ""  # sale, buy, repair, review, rent, wanted
    all_intents: list[str] = field(default_factory=list)
    reject_intents: list[str] = field(default_factory=list)


@dataclass
class EntityExtractionResult:
    text: str
    normalized_text: str
    tokens: list[str]
    intents: Intents = field(default_factory=Intents)
    dictionary_matches: list[DictionaryMatch] = field(default_factory=list)
    prices: list[ExtractedPrice] = field(default_factory=list)
    numeric_specs: list[ExtractedNumericSpec] = field(default_factory=list)
    has_explicit_price: bool = False
    has_specs: bool = False


# ── Price extraction ────────────────────────────────────────────────

PRICE_PATTERNS = [
    # "100000 руб", "100 000 руб", "100000р", "1200₽"
    re.compile(r"(\d[\d\s]*\d|\d)\s*(?:руб|rub|р\.|р|₽)(?:\b|\.|,|$)", re.IGNORECASE),
    # "руб 100000", "rub 50000"
    re.compile(r"(?:руб|rub|р\.?)\s*(\d[\d\s]*\d|\d)\b", re.IGNORECASE),
    # "$1000", "$ 1000", "1000$"
    re.compile(r"\$\s*(\d[\d\s]*\d|\d)\b"),
    re.compile(r"(\d[\d\s]*\d|\d)\s*\$"),
    # "€1000", "1000€"
    re.compile(r"€\s*(\d[\d\s]*\d|\d)\b"),
    re.compile(r"(\d[\d\s]*\d|\d)\s*€"),
    # "1000 usd", "1000 eur"
    re.compile(r"(\d[\d\s]*\d|\d)\s*(?:usd|eur|euro|доллар|долларов)\b", re.IGNORECASE),
]

CURRENCY_WORDS = {
    "руб": "rub",
    "rub": "rub",
    "р": "rub",
    "₽": "rub",
    "$": "usd",
    "usd": "usd",
    "€": "eur",
    "eur": "eur",
    "euro": "eur",
}

# Word-token price: "цена 120000" or "120000 руб"
WORD_CURRENCY_RE = re.compile(
    r"(?:цена|price|цене|стоит|стоимость|отдам за|продам за|за)\s*"
    r"(\d[\d\s]*\d|\d)\b(?!\s*[a-zа-я])",
    re.IGNORECASE,
)
PRICE_BEFORE_CURRENCY_RE = re.compile(r"(\d[\d\s]*\d)\s*([а-яa-z]{2,6})\b", re.IGNORECASE)


def extract_price(text: str) -> list[ExtractedPrice]:
    """Extract price mentions from text."""
    prices: list[ExtractedPrice] = []

    for pattern in PRICE_PATTERNS:
        for match in pattern.finditer(text):
            value_str = match.group(1).replace(" ", "").replace("\u00a0", "")
            try:
                value = float(value_str)
                if "₽" in match.group(0) or "руб" in match.group(0).lower():
                    currency = "rub"
                elif "$" in match.group(0):
                    currency = "usd"
                elif "€" in match.group(0):
                    currency = "eur"
                else:
                    currency = "rub"
                prices.append(
                    ExtractedPrice(
                        value=value,
                        currency=currency,
                        raw=match.group(0),
                        source="explicit",
                    )
                )
            except ValueError:
                continue

    # Word-based: "цена 120000"
    for match in WORD_CURRENCY_RE.finditer(text):
        value_str = match.group(1).replace(" ", "").replace("\u00a0", "")
        try:
            value = float(value_str)
            prices.append(
                ExtractedPrice(value=value, currency="rub", raw=match.group(0), source="per_word")
            )
        except ValueError:
            continue

    return prices


# ── Numeric spec extraction ─────────────────────────────────────────

# Common Russian measurement units and their normalized form
UNIT_MAP = {
    "дюйм": "inch",
    "дюйма": "inch",
    "дюймов": "inch",
    "inch": "inch",
    "inches": "inch",
    "in": "inch",
    '"': "inch",
    "мм": "mm",
    "mm": "mm",
    "см": "cm",
    "cm": "cm",
    "гб": "gb",
    "gb": "gb",
    "гигабайт": "gb",
    "терабайт": "tb",
    "tb": "tb",
    "тб": "tb",
    "гц": "ghz",
    "ghz": "ghz",
    "кг": "kg",
    "kg": "kg",
    "грамм": "g",
    "г": "g",
}

# Entity-specific extraction patterns
ENTITY_PATTERNS: dict[str, list[re.Pattern]] = {
    "diagonal_inches": [
        re.compile(r"(\d{2,3}(?:[.,]\d)?)\s*(?:дюйм[аов]*|inch(?:es)?|\"|in)\b", re.IGNORECASE),
        re.compile(r"(\d{2,3}(?:[.,]\d)?)\s*\"\s*(?:дюйм|диагональ)?", re.IGNORECASE),
    ],
    "storage_gb": [
        re.compile(r"(\d{3,4})\s*(?:гб|gb|гигабайт)\b", re.IGNORECASE),
    ],
    "storage_tb": [
        re.compile(r"(\d{1,2})\s*(?:тб|tb|терабайт)\b", re.IGNORECASE),
    ],
    "ram_gb": [
        re.compile(r"(\d{1,3})\s*(?:гб|gb)\s*(?:ram|озу|оператив[н]?[ая]?)\b", re.IGNORECASE),
        re.compile(r"(?:ram|озу|оператив[н]?[ая]?)\s*(\d{1,3})\s*(?:гб|gb)\b", re.IGNORECASE),
    ],
    "price_value": [
        re.compile(r"(\d{4,8})\s*(?:руб|rub|р|₽)\b", re.IGNORECASE),
    ],
}


def extract_numeric_specs(text: str) -> list[ExtractedNumericSpec]:
    """Extract numeric specifications from text."""
    specs: list[ExtractedNumericSpec] = []

    for entity, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                value_str = match.group(1).replace(",", ".").replace(" ", "")
                try:
                    value = float(value_str)
                    unit = ""
                    if "inch" in entity or "diagonal" in entity:
                        unit = "inch"
                    elif "gb" in entity:
                        unit = "gb"
                    elif "tb" in entity:
                        unit = "tb"
                    specs.append(
                        ExtractedNumericSpec(
                            entity=entity,
                            value=value,
                            unit=unit,
                            raw=match.group(0),
                        )
                    )
                except ValueError:
                    continue

    return specs


# ── Intent extraction ───────────────────────────────────────────────

INTENT_DICTIONARIES: dict[str, list[str]] = {
    "sale": [
        "продам", "продаю", "продается", "продаётся", "в продаже",
        "отдам", "уступлю", "есть в наличии", "в наличии",
        "sell", "selling", "forsale",
        "цена", "price", "стоит", "стоимость",
    ],
    "buy": [
        "куплю", "покупаю", "ищу", "нужен", "нужна", "нужно",
        "приобрету", "рассмотрю покупку", "wanted",
    ],
    "repair": [
        "ремонт", "починю", "чиню", "запчасти", "разбор", "донор",
    ],
    "review": [
        "отзыв", "обзор", "review", "тест", "тестирование",
        "стоит ли", "какой лучше", "посоветуйте",
    ],
    "rent": [
        "аренда", "сдам", "сниму", "rent", "арендую",
    ],
    "wanted": [
        "ищу", "нужен", "нужна", "нужно", "wanted", "looking for",
    ],
}

# Negative / rejection intents
REJECT_DICTIONARIES: dict[str, list[str]] = {
    "fake": [
        "копия", "реплика", "не оригинал", "паль", "люкс копия",
        "mastercopy", "подделка", "копию",
    ],
    "accessory": [
        "чехол", "кабель", "коробка", "амбушюры", "зарядка",
        "пульт", "кронштейн", "подставка", "наушники", "защитное стекло",
    ],
}


def extract_intents(tokens: list[str]) -> Intents:
    """Detect intents from tokenized text."""
    result = Intents()
    text = " ".join(tokens).lower()

    # Check primary intents
    for intent, trigger_words in INTENT_DICTIONARIES.items():
        for word in trigger_words:
            if word in text:
                result.all_intents.append(intent)
                if not result.primary:
                    result.primary = intent
                break

    # Check reject intents
    for intent, trigger_words in REJECT_DICTIONARIES.items():
        for word in trigger_words:
            if word in text:
                result.reject_intents.append(intent)
                break

    return result


# ── Dictionary matching ─────────────────────────────────────────────


def match_dictionaries(
    tokens: list[str],
    dictionaries: tuple[CompiledDictionary, ...],
    max_edit_distance: int = 1,
    min_term_length: int = 5,
) -> list[DictionaryMatch]:
    """Match tokens against compiled dictionaries."""
    matches: list[DictionaryMatch] = []

    for d in dictionaries:
        # Single-token exact match
        for token in tokens:
            if token in d.terms:
                matches.append(
                    DictionaryMatch(canonical=d.canonical, term=token, confidence=1.0)
                )

        # Multi-token exact match
        for i in range(len(tokens)):
            for mtt_len in range(2, 5):
                if i + mtt_len <= len(tokens):
                    phrase = tuple(tokens[i : i + mtt_len])
                    if phrase in d.multi_token_terms:
                        matches.append(
                            DictionaryMatch(
                                canonical=d.canonical,
                                term=" ".join(phrase),
                                confidence=1.0,
                            )
                        )

        # Fuzzy single-token match (edit distance)
        if max_edit_distance > 0:
            for token in tokens:
                if len(token) >= min_term_length and token not in d.terms:
                    for dict_term in d.terms:
                        dist = levenshtein_distance(token, dict_term)
                        if 0 < dist <= max_edit_distance:
                            confidence = 1.0 - (dist / max(len(token), len(dict_term)))
                            matches.append(
                                DictionaryMatch(
                                    canonical=d.canonical,
                                    term=token,
                                    confidence=max(confidence, 0.5),
                                )
                            )
                            break

    return matches


# ── Main extraction function ────────────────────────────────────────


def extract_entities(
    normalized_text: str,
    dictionaries: tuple[CompiledDictionary, ...] | None = None,
    max_edit_distance: int = 1,
    min_term_length: int = 5,
) -> EntityExtractionResult:
    """Full entity extraction from normalized text."""
    tokens = normalized_text.lower().split() if normalized_text else []

    intents = extract_intents(tokens)
    prices = extract_price(normalized_text)
    numeric_specs = extract_numeric_specs(normalized_text)
    dict_matches = (
        match_dictionaries(tokens, dictionaries, max_edit_distance, min_term_length)
        if dictionaries
        else []
    )

    return EntityExtractionResult(
        text=normalized_text,
        normalized_text=normalized_text,
        tokens=tokens,
        intents=intents,
        dictionary_matches=dict_matches,
        prices=prices,
        numeric_specs=numeric_specs,
        has_explicit_price=bool(prices),
        has_specs=bool(numeric_specs),
    )
