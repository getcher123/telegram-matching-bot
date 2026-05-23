"""Test fixtures and YAML loaders for parameterized tests."""

from __future__ import annotations

from pathlib import Path

import yaml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_yaml_cases(relative_path: str) -> list[dict]:
    """Load test cases from a YAML fixtures file."""
    path = FIXTURES_DIR / relative_path
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


def load_config(path: str) -> dict:
    """Load a YAML config fixture."""
    full_path = FIXTURES_DIR / path if not path.startswith("/") else Path(path)
    with open(full_path, encoding="utf-8") as f:
        return yaml.safe_load(f)
