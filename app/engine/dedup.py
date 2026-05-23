"""Duplicate detection for message processing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.storage.repository import Repository


@dataclass
class DuplicateCheckResult:
    is_duplicate: bool
    normalized_hash: str
    existing_message_id: int | None = None


class DedupService:
    """Service for detecting duplicate messages."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    @staticmethod
    def hash_normalized(text: str) -> str:
        """Create stable hash of normalized text for dedup lookup."""
        text = text.lower().strip()
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def check(self, normalized_text: str) -> DuplicateCheckResult:
        """Check if normalized text is a duplicate."""
        text_hash = self.hash_normalized(normalized_text)
        existing = await self._repo.find_by_normalized_hash(text_hash)

        return DuplicateCheckResult(
            is_duplicate=existing is not None,
            normalized_hash=text_hash,
            existing_message_id=existing,
        )

    async def record(self, normalized_text: str) -> str:
        """Record a normalized text hash in the store."""
        text_hash = self.hash_normalized(normalized_text)
        await self._repo.save_normalized_hash(text_hash)
        return text_hash
