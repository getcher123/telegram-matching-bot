"""Tests for storage models and repository."""

from __future__ import annotations

import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.storage.models import AlertOrm, Base, MatchOrm, MessageOrm
from app.storage.repository import AlertRepository, MatchRepository, MessageRepository


@pytest_asyncio.fixture
async def session():
    """Create in-memory SQLite session for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as s:
        yield s

    await engine.dispose()


@pytest.mark.asyncio
async def test_save_message(session: AsyncSession):
    """BL-0701: Сохранение сообщения."""
    repo = MessageRepository(session)
    msg = MessageOrm(
        telegram_message_id=123,
        chat_peer="@test_chat",
        chat_title="Test Chat",
        raw_text="Продам MacBook Pro",
        normalized_text="продам macbook pro",
        message_timestamp=datetime.datetime.now(datetime.UTC),
        text_hash="abc123",
    )
    msg_id = await repo.save(msg)
    assert msg_id > 0

    count = await repo.count()
    assert count == 1


@pytest.mark.asyncio
async def test_find_message_by_telegram_id(session: AsyncSession):
    """BL-0701: Поиск по telegram ID."""
    repo = MessageRepository(session)
    msg = MessageOrm(
        telegram_message_id=456,
        chat_peer="@test_chat",
        raw_text="Test",
        message_timestamp=datetime.datetime.now(datetime.UTC),
        text_hash="def456",
    )
    await repo.save(msg)

    found = await repo.find_by_telegram_id(456, "@test_chat")
    assert found is not None
    assert found.raw_text == "Test"

    not_found = await repo.find_by_telegram_id(999, "@test_chat")
    assert not_found is None


@pytest.mark.asyncio
async def test_save_match(session: AsyncSession):
    """BL-0701: Сохранение совпадения."""
    msg_repo = MessageRepository(session)
    msg = MessageOrm(
        telegram_message_id=1,
        chat_peer="@test",
        raw_text="test",
        message_timestamp=datetime.datetime.now(datetime.UTC),
        text_hash="aaa",
    )
    msg_id = await msg_repo.save(msg)

    match_repo = MatchRepository(session)
    match = MatchOrm(
        message_id=msg_id,
        rule_id="tv_50_plus_sale",
        rule_title="TV 50+",
        score=150.0,
        decision="MATCH",
        config_hash="cfg123",
        evidence_json='{"tv": 40}',
    )
    match_id = await match_repo.save(match)
    assert match_id > 0

    count = await match_repo.count_by_rule("tv_50_plus_sale")
    assert count == 1


@pytest.mark.asyncio
async def test_save_alert(session: AsyncSession):
    """BL-0701: Сохранение алерта."""
    msg_repo = MessageRepository(session)
    msg = MessageOrm(
        telegram_message_id=2,
        chat_peer="@test",
        raw_text="test",
        message_timestamp=datetime.datetime.now(datetime.UTC),
        text_hash="bbb",
    )
    msg_id = await msg_repo.save(msg)

    match_repo = MatchRepository(session)
    match = MatchOrm(message_id=msg_id, rule_id="test_rule", config_hash="h1")
    match_id = await match_repo.save(match)

    alert_repo = AlertRepository(session)
    alert = AlertOrm(match_id=match_id, target="@user", status="sent")
    alert_id = await alert_repo.save(alert)
    assert alert_id > 0

    count = await alert_repo.count()
    assert count == 1
