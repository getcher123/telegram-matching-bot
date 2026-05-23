"""Config versioning and hashing."""

from __future__ import annotations

import hashlib


def compute_config_hash(yaml_content: str) -> str:
    """Compute stable SHA-256 hash of raw YAML content."""
    return hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()
