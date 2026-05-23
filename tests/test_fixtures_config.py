"""Test config loading from fixture YAML files."""

from __future__ import annotations

from pathlib import Path

from app.config.loader import ConfigService

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "config"


def test_valid_config_loads() -> None:
    """Test that valid config loads without error."""
    path = str(FIXTURES_DIR / "watch_config.valid.yaml")
    service = ConfigService(config_path=path)
    config = service.load()
    assert config is not None
    assert len(config.rules) == 3
    rule_ids = {r.id for r in config.rules}
    assert "tv_50_plus_sale" in rule_ids
    assert "macbook_m4_pro_sale" in rule_ids
    assert "airpods_pro_2_sale" in rule_ids
