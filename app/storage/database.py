"""Database engine and session factory."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.storage.models import Base


def create_engine(sqlite_path: str = "./var/db/tg_market_watch.sqlite3") -> AsyncEngine:
    """Create async SQLAlchemy engine for SQLite."""
    db_path = Path(sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+aiosqlite:///{db_path.resolve()}"
    return create_async_engine(url, echo=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Create async session factory."""
    return async_sessionmaker(engine, expire_on_commit=False)
