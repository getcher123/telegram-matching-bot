"""Text normalization pipeline for Russian product listings."""

from __future__ import annotations

import re
import unicodedata

# ── Unicode normalisation ──────────────────────────────────────────

ZERO_WIDTH_CHARS = {
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\ufeff",  # BOM / ZERO WIDTH NO-BREAK SPACE
    "\u2060",  # WORD JOINER
}

QUOTE_MAP = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u00ab": '"',
        "\u00bb": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
    }
)

DASH_MAP = str.maketrans(
    {
        "\u2013": "-",  # en-dash
        "\u2014": "-",  # em-dash
        "\u2212": "-",  # minus sign
    }
)

CURRENCY_MAP = str.maketrans(
    {
        "$": " usd ",
        "\u20bd": " rub ",
        "\u20ac": " eur ",
        "\u00a3": " gbp ",
        "\u00a5": " cny ",
    }
)

# Cyrillic → Latin confusables for known Latin tokens
CYRILLIC_TO_LATIN_CONFUSABLES = str.maketrans(
    {
        "а": "a",
        "с": "c",
        "е": "e",
        "к": "k",
        "м": "m",
        "о": "o",
        "р": "p",
        "т": "t",
        "х": "x",
        "у": "y",
        "в": "b",
        "н": "h",
    }
)

# Known Latin tokens that when seen with Cyrillic confusables should be fixed
KNOWN_LATIN_TOKENS = frozenset({
    "airpods", "air", "pods",
    "macbook", "mac", "book",
    "m4", "m4pro", "pro",
    "oled", "qled", "uhd", "mini-led",
    "bravia", "samsung", "lg", "sony", "tcl",
    "hisense", "xiaomi", "philips", "haier", "panasonic",
    "apple", "inch", "inches", "usb", "usb-c", "type-c",
    "gb", "tb", "ssd", "ram", "cpu", "gpu",
    "tv",
})

# Typo corrections for common misspellings
TYPO_CORRECTIONS = {
    "телевизар": "телевизор",
    "теливизор": "телевизор",
    "телвизор": "телевизор",
    "макбуук": "макбук",
    "мак бук": "макбук",
    "аирподс": "airpods",
    "эйрподс": "airpods",
    "айрподс": "airpods",
    "аир подс": "airpods",
    "air pods": "airpods",
}

NON_ALPHA_RE = re.compile(r"[^a-zа-яё0-9]+")


class NormalizationConfig:
    """Local config for normalization pipeline steps."""

    def __init__(
        self,
        unicode_nfkc: bool = True,
        lowercase: bool = True,
        replace_yo_with_e: bool = True,
        remove_zero_width_chars: bool = True,
        normalize_quotes: bool = True,
        normalize_dashes: bool = True,
        normalize_currency: bool = True,
        fix_confusable_scripts: bool = True,
        collapse_repeated_spaces: bool = True,
        max_edit_distance_for_dictionary_terms: int = 1,
        use_edit_distance_only_for_terms_min_length: int = 5,
        token_window_for_context: int = 8,
    ):
        self.unicode_nfkc = unicode_nfkc
        self.lowercase = lowercase
        self.replace_yo_with_e = replace_yo_with_e
        self.remove_zero_width_chars = remove_zero_width_chars
        self.normalize_quotes = normalize_quotes
        self.normalize_dashes = normalize_dashes
        self.normalize_currency = normalize_currency
        self.fix_confusable_scripts = fix_confusable_scripts
        self.collapse_repeated_spaces = collapse_repeated_spaces
        self.max_edit_distance_for_dictionary_terms = max_edit_distance_for_dictionary_terms
        self.use_edit_distance_only_for_terms_min_length = (
            use_edit_distance_only_for_terms_min_length
        )
        self.token_window_for_context = token_window_for_context


def normalize_text(text: str, config: NormalizationConfig | None = None) -> str:
    """Run full normalization pipeline on input text."""
    cfg = config or NormalizationConfig()
    result = text

    # Step 1: Unicode NFKC
    if cfg.unicode_nfkc:
        result = unicodedata.normalize("NFKC", result)

    # Step 2: Remove zero-width chars
    if cfg.remove_zero_width_chars:
        result = "".join(c for c in result if c not in ZERO_WIDTH_CHARS)

    # Step 3: Normalize quotes
    if cfg.normalize_quotes:
        result = result.translate(QUOTE_MAP)

    # Step 4: Normalize dashes
    if cfg.normalize_dashes:
        result = result.translate(DASH_MAP)

    # Step 5: Normalize currency
    if cfg.normalize_currency:
        result = result.translate(CURRENCY_MAP)

    # Step 6: Lowercase
    if cfg.lowercase:
        result = result.lower()

    # Step 7: Replace ё → е
    if cfg.replace_yo_with_e:
        result = result.replace("ё", "е")

    # Step 8: Newlines → spaces
    result = result.replace("\n", " ")
    result = result.replace("\r", " ")

    # Step 9: Expand "к" shorthand for thousands (35к → 35000)
    result = re.sub(r"(\d+)\s*к\b", lambda m: str(int(m.group(1)) * 1000), result)

    # Step 10: Fix confusable scripts — per-token Cyrillic ↔ Latin normalization
    if cfg.fix_confusable_scripts:
        result = _fix_token_scripts(result)

    # Step 11: Apply typo corrections
    result = _apply_typo_corrections(result)

    # Step 12: Remove spaces between digits for thousand separators (1 200 → 1200)
    # Only merge when the second group is exactly 3 digits (thousands separator pattern)
    result = re.sub(r"(\d)\s+(\d{3})(?!\d)", lambda m: m.group(1) + m.group(2), result)

    # Step 13: Compound splitting (m4pro → m4 pro, pro2 → pro 2)
    result = re.sub(
        r"\b(m4pro|м4про)\b",
        lambda m: {"m4pro": "m4 pro", "м4про": "м4 про"}.get(m.group(1), m.group(1)),
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"\b(pro2|про2)\b",
        lambda m: {"pro2": "pro 2", "про2": "про 2"}.get(m.group(1), m.group(1)),
        result,
        flags=re.IGNORECASE,
    )

    # Step 14: Roman numeral II → 2 (case-insensitive)
    result = re.sub(r"\bii\b", "2", result)

    # Step 15: Collapse spaces
    if cfg.collapse_repeated_spaces:
        result = re.sub(r"\s+", " ", result).strip()

    return result


def _has_cyrillic(text: str) -> bool:
    """Check if text contains any Cyrillic letters."""
    return any("Ѐ" <= c <= "ӿ" or "Ԁ" <= c <= "ԯ" for c in text)


def _has_latin(text: str) -> bool:
    """Check if text contains any Latin letters."""
    return any("a" <= c <= "z" for c in text)


def _is_pure_latin(text: str) -> bool:
    """Check if text contains only Latin letters (no Cyrillic at all)."""
    return not _has_cyrillic(text)


def _fix_token_scripts(text: str) -> str:
    """Fix confusable scripts per-token.

    - Tokens with MIXED Cyrillic+Latin: normalize to Cyrillic (stray Latin → Cyrillic)
    - Tokens where Cyrillic→Latin produces a known token: convert to Latin
    - Pure Latin tokens: leave as-is
    - Pure Cyrillic tokens: leave as-is (typo corrections handle misspellings)
    """
    tokens = text.split()
    result = []
    for token in tokens:
        # Strip trailing punctuation for matching, keep original
        cleaned = token.rstrip(",.!?;:()[]{}\"'")
        punct = token[len(cleaned):]

        if not _has_cyrillic(cleaned):
            # Pure Latin — keep as-is
            result.append(token)
            continue

        if not _has_latin(cleaned):
            # Pure Cyrillic — keep as-is
            result.append(token)
            continue

        # Mixed script: try Cyrillic→Latin conversion first
        latinized = _cyrillic_to_latin_for_known(cleaned)
        if latinized in KNOWN_LATIN_TOKENS:
            result.append(latinized + punct)
            continue

        # Not a known token — normalize stray Latin → Cyrillic
        # Only convert Latin letters that have Cyrillic lookalikes
        cyrillified = _latin_to_cyrillic_in_token(cleaned)
        result.append(cyrillified + punct)

    return " ".join(result)


def _cyrillic_to_latin_for_known(text: str) -> str:
    """Convert Cyrillic confusables to Latin."""
    return text.translate(CYRILLIC_TO_LATIN_CONFUSABLES)


def _latin_to_cyrillic_in_token(text: str) -> str:
    """Convert Latin letters in a mixed-script token to Cyrillic."""
    # Only convert letters that have direct Cyrillic counterparts
    mapping = {
        "a": "а", "c": "с", "e": "е", "k": "к", "m": "м",
        "o": "о", "p": "р", "t": "т", "x": "х", "y": "у",
        "b": "в", "h": "н",
        "l": "л", "i": "и", "v": "в",
    }
    result = []
    for char in text:
        result.append(mapping.get(char, char))
    return "".join(result)


def _apply_typo_corrections(text: str) -> str:
    """Apply known typo corrections."""
    result = text
    for wrong, correct in TYPO_CORRECTIONS.items():
        result = re.sub(rf"\b{re.escape(wrong)}\b", correct, result)
    return result


def tokenize(text: str) -> list[str]:
    """Split normalized text into tokens (whitespace-delimited)."""
    return text.split()


def get_context_window(tokens: list[str], center: int, window: int = 8) -> list[str]:
    """Get tokens around a center index within window size."""
    start = max(0, center - window)
    end = min(len(tokens), center + window + 1)
    return tokens[start:end]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(
                    curr_row[j] + 1,
                    prev_row[j + 1] + 1,
                    prev_row[j] + cost,
                )
            )
        prev_row = curr_row

    return prev_row[-1]


WORD_BOUNDARY = re.compile(r"\w+")


def extract_digit_words(text: str) -> list[str]:
    """Extract sequences that contain digits (for price, model numbers)."""
    return WORD_BOUNDARY.findall(text)


def is_latin_heavy(text: str) -> bool:
    """Check if text is predominantly Latin letters (possible layout error)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin_count = sum(1 for c in letters if "a" <= c <= "z" or "A" <= c <= "Z")
    return latin_count / len(letters) > 0.6
