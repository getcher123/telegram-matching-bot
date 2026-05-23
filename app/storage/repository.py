"""Repository layer for messages, matches, and alerts."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import AlertOrm, MatchOrm, MessageOrm


class MessageRepository:
    """Repository for message storage and lookup."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, msg: MessageOrm) -> int:
        self._session.add(msg)
        await self._session.flush()
        return msg.id

    async def find_by_telegram_id(self, telegram_id: int, chat_peer: str) -> MessageOrm | None:
        stmt = select(MessageOrm).where(
            MessageOrm.telegram_message_id == telegram_id,
            MessageOrm.chat_peer == chat_peer,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        stmt = select(func.count(MessageOrm.id))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def recent(self, limit: int = 50) -> list[MessageOrm]:
        stmt = select(MessageOrm).order_by(MessageOrm.received_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class MatchRepository:
    """Repository for rule match storage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, match: MatchOrm) -> int:
        self._session.add(match)
        await self._session.flush()
        return match.id

    async def count_by_rule(self, rule_id: str) -> int:
        stmt = select(func.count(MatchOrm.id)).where(MatchOrm.rule_id == rule_id)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def recent(self, limit: int = 50) -> list[MatchOrm]:
        stmt = select(MatchOrm).order_by(MatchOrm.matched_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class AlertRepository:
    """Repository for alert storage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, alert: AlertOrm) -> int:
        self._session.add(alert)
        await self._session.flush()
        return alert.id

    async def count(self) -> int:
        stmt = select(func.count(AlertOrm.id))
        result = await self._session.execute(stmt)
        return result.scalar() or 0


class UnitOfWork:
    """Unit of work for coordinated persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.messages = MessageRepository(session)
        self.matches = MatchRepository(session)
        self.alerts = AlertRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
