"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.models import ConfigVersion


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.config_version = ConfigVersion(
        config_hash="",
        version=0,
        rules_count=0,
        enabled_rules_count=0,
    )
    yield
    # Shutdown


app = FastAPI(
    title="tg-market-watch",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "app": "tg-market-watch"}