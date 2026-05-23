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

# Cyrillic / Latin confusables (common swapped letters)
MIXED_CYRILLIC_LATIN = str.maketrans(
    {
        "a": "а",  # Latin a → Cyrillic а
        "e": "е",  # Latin e → Cyrillic е
        "o": "о",  # Latin o → Cyrillic о
        "c": "с",  # Latin c → Cyrillic с
        "p": "р",  # Latin p → Cyrillic р
        "x": "х",  # Latin x → Cyrillic х
        "y": "у",  # Latin y → Cyrillic у
        "A": "А",
        "B": "В",
        "C": "С",
        "E": "Е",
        "H": "Н",
        "K": "К",
        "M": "М",
        "O": "О",
        "P": "Р",
        "T": "Т",
        "X": "Х",
        "Y": "У",
    }
)

# Latin → Cyrillic keyboard layout flip (for typos like 'ghbdtn' → 'привет')
LAYOUT_LATIN_TO_CYRILLIC = str.maketrans(
    {
        "q": "й",
        "w": "ц",
        "e": "у",
        "r": "к",
        "t": "е",
        "y": "н",
        "u": "г",
        "i": "ш",
        "o": "щ",
        "p": "з",
        "[": "х",
        "]": "ъ",
        "a": "ф",
        "s": "ы",
        "d": "в",
        "f": "а",
        "g": "п",
        "h": "р",
        "j": "о",
        "k": "л",
        "l": "д",
        ";": "ж",
        "'": "э",
        "z": "я",
        "x": "ч",
        "c": "с",
        "v": "м",
        "b": "и",
        "n": "т",
        "m": "ь",
        ",": "б",
        ".": "ю",
    }
)

# Known product terms where transliteration is safe
PRODUCT_TRANSLIT_MAP = {
    "macbook": "макбук",
    "airpods": "эйрподс",
    "iphone": "айфон",
    "ipad": "айпад",
    "imac": "аймак",
    "watch": "вотч",
    "samsung": "самсунг",
    "xiaomi": "сяоми",
    "huawei": "хуавей",
    "honor": "хонор",
    "lenovo": "леново",
    "dell": "делл",
    "hp": "эйч пи",
    "apple": "эппл",
    "asus": "асус",
    "acer": "асер",
    "msi": "эмэс ай",
    "gigabyte": "гигабайт",
    "playstation": "плейстейшен",
    "play station": "плейстейшен",
    "xbox": "иксбокс",
    "nintendo": "нинтендо",
    "switch": "свитч",
    "sony": "сони",
    "canon": "канон",
    "nikon": " nik on",
    "lg": "эл джи",
    "jbl": "джей би эл",
    "logitech": "лоджитек",
    "razer": "рейзер",
    "steelseries": "стил сериес",
    "hyperx": "гипер икс",
}

# Regular expression to tokenize
TOKEN_RE = re.compile(r"")


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
        fix_mixed_cyrillic_latin_for_known_terms: bool = True,
        fix_keyboard_layout_for_known_terms: bool = False,
        transliterate_known_product_terms: bool = True,
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
        self.fix_mixed_cyrillic_latin_for_known_terms = fix_mixed_cyrillic_latin_for_known_terms
        self.fix_keyboard_layout_for_known_terms = fix_keyboard_layout_for_known_terms
        self.transliterate_known_product_terms = transliterate_known_product_terms
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

    # Step 8: Transliterate known product terms
    if cfg.transliterate_known_product_terms:
        result = _transliterate_known(result)

    # Step 9: Fix keyboard layout — only for purely Latin text (no Cyrillic present)
    if cfg.fix_keyboard_layout_for_known_terms and _is_pure_latin(result):
        result = _fix_keyboard_layout(result)

    # Step 10: Fix mixed Cyrillic/Latin — only if text has some Cyrillic
    if cfg.fix_mixed_cyrillic_latin_for_known_terms and not _is_pure_latin(result):
        result = _fix_mixed_script(result)

    # Step 11: Collapse spaces
    if cfg.collapse_repeated_spaces:
        result = re.sub(r"\s+", " ", result).strip()

    return result


def _fix_mixed_script(text: str) -> str:
    """Replace latin-looking letters with cyrillic equivalents for common substitute patterns."""
    return text.translate(MIXED_CYRILLIC_LATIN)


def _fix_keyboard_layout(text: str) -> str:
    """Convert text typed in wrong keyboard layout back to intended cyrillic."""
    result = []
    for char in text:
        if "a" <= char <= "z":
            cyrillic = char.translate(LAYOUT_LATIN_TO_CYRILLIC)
            result.append(cyrillic)
        else:
            result.append(char)
    return "".join(result)


def _transliterate_known(text: str) -> str:
    """Apply known product transliterations."""
    result = text
    for latin, cyrillic in PRODUCT_TRANSLIT_MAP.items():
        # Replace whole words only (not substrings)
        result = re.sub(rf"\b{re.escape(latin)}\b", cyrillic, result)
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


def _is_pure_latin(text: str) -> bool:
    """Check if text contains only Latin letters (no Cyrillic at all)."""
    return all(not ("\u0400" <= c <= "\u04ff" or "\u0500" <= c <= "\u052f") for c in text)
