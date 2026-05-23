"""FastAPI application with full lifespan and routing."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import auth, health, status
from app.config.loader import ConfigService
from app.core.app_state import AppState
from app.engine.pipeline import ProcessingPipeline
from app.storage.database import DatabaseManager
from app.storage.repository import Repository

logger = logging.getLogger(__name__)

DATA_DIR = Path("./var")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    state = AppState()
    state.component_status["app"] = "starting"

    # ── Init ConfigService ──
    try:
        state.config_service = ConfigService()
        state.config_service.load()
        state.config_version = state.config_service.version_info()
        state.component_status["config"] = "ok"
        logger.info("Config loaded: hash=%s", state.config_version.config_hash)
    except Exception:
        state.component_status["config"] = "error"
        logger.exception("Failed to load config")
        raise

    # ── Init DB ──
    try:
        db_path = DATA_DIR / "data" / "marketwatch.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        state.database = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
        await state.database.create_all()
        state.repository = Repository(state.database.uow())
        state.component_status["db"] = "ok"
    except Exception:
        state.component_status["db"] = "error"
        logger.exception("Failed to init database")

    # ── Init Pipeline ──
    if state.config_service and state.repository:
        state.pipeline = ProcessingPipeline(
            config_svc=state.config_service,
            repository=state.repository,
        )
        state.component_status["pipeline"] = "ok"

    app.state.app_state = state
    state.component_status["app"] = "running"
    logger.info("tg-market-watch started")

    yield

    # ── Shutdown ──
    state.component_status["app"] = "stopped"
    if state.database:
        await state.database.close()
    logger.info("tg-market-watch stopped")


app = FastAPI(
    title="tg-market-watch",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(status.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    return {"app": "tg-market-watch", "docs": "/docs"}
