"""Database engine and session factory."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.storage.models import Base
from app.storage.repository import UnitOfWork


class DatabaseManager:
    """Manages database lifecycle: engine, sessions, tables."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker | None = None

    async def _ensure_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(self._url, echo=False)
            self._session_factory = async_sessionmaker(
                self._engine, expire_on_commit=False
            )
        return self._engine

    async def create_all(self) -> None:
        """Create all tables."""
        engine = await self._ensure_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def uow(self) -> UnitOfWork:
        """Create a UnitOfWork with a new session."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call create_all first.")
        session = self._session_factory()
        return UnitOfWork(session)

    async def close(self) -> None:
        """Dispose engine."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


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
