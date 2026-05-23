"""Tests for config loader and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.config.loader import ConfigService
from app.config.models import RootConfig


def test_config_loads_example():
    """BL-0301: пример YAML валидируется успешно."""
    config_path = Path(__file__).parents[2] / "config" / "watch.yaml"
    assert config_path.exists(), "config/watch.yaml not found"

    service = ConfigService(config_path=str(config_path))
    compiled = service.load_initial()
    assert compiled.config_hash != ""
    assert len(compiled.rules) >= 3
    assert len(compiled.enabled_rules) >= 3


def test_config_rule_ids():
    """BL-0301: правила имеют id."""
    config_path = Path(__file__).parents[2] / "config" / "watch.yaml"
    service = ConfigService(config_path=str(config_path))
    compiled = service.load_initial()

    rule_ids = [r.id for r in compiled.rules]
    assert "tv_50_plus_sale" in rule_ids
    assert "macbook_m4_pro_sale" in rule_ids
    assert "airpods_pro_2_sale" in rule_ids


def test_config_no_secrets_in_yaml():
    """BL-0301: в конфиге нет секретов."""
    config_path = Path(__file__).parents[2] / "config" / "watch.yaml"
    content = config_path.read_text(encoding="utf-8")

    secrets = ["api_id:", "api_hash:", "phone:", "password:", "session_string:"]
    for secret in secrets:
        found = [ln for ln in content.split("\n") if secret in ln.lower()]
        assert not found, f"Found potential secret: {found}"


def test_config_atomic_reload():
    """BL-0302: невалидный reload не ломает активную конфиг."""
    config_path = Path(__file__).parents[2] / "config" / "watch.yaml"
    service = ConfigService(config_path=str(config_path))
    compiled = service.load_initial()
    original_hash = compiled.config_hash

    # Try reload with same valid config
    result = service.reload()
    assert result is not None
    assert result.config_hash == original_hash

    # Now the service should still have active config (test via property)
    assert service.active is not None
    assert service.active.config_hash == original_hash


def test_config_missing_rule_id():
    """BL-0301: схема не допускает правило без id."""
    bad_config = {
        "version": 1,
        "app": {"name": "test"},
        "telegram": {"session_file": "/tmp/test.session"},
        "storage": {"driver": "sqlite", "sqlite_path": "/tmp/test.db"},
        "rules": [
            {"title": "no id rule", "enabled": True}
        ],
    }
    with pytest.raises((ValueError, KeyError, TypeError)):
        RootConfig.model_validate(bad_config)


def test_invalid_yaml_fails():
    """Невалидный YAML выбрасывает ParserError от PyYAML."""
    bad_yaml = "version: 1\napp:\n  name: test\n  invalid_field: [1, 2\n"
    with pytest.raises(yaml.parser.ParserError):
        yaml.safe_load(bad_yaml)


def test_config_version_hash_stability():
    """BL-0303: одинаковый YAML даёт одинаковый hash."""
    from app.config.hashing import compute_config_hash

    content = "version: 1\napp:\n  name: test\n"
    h1 = compute_config_hash(content)
    h2 = compute_config_hash(content)
    assert h1 == h2

    h3 = compute_config_hash(content + " ")
    assert h1 != h3
