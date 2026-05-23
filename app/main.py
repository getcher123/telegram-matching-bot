"""FastAPI application with full lifespan and routing."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, health, status
from app.core.app_state import AppState


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    app.state.app_state = AppState()
    app.state.app_state.component_status["app"] = "starting"
    yield
    # Shutdown
    app.state.app_state.component_status["app"] = "stopped"


app = FastAPI(
    title="tg-market-watch",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health.router)
app.include_router(status.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    return {"app": "tg-market-watch", "docs": "/docs"}
