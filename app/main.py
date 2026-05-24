"""FastAPI application with full lifespan and routing."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.alerts.dispatcher import AlertDispatcher
from app.api.routes import auth, health, status
from app.config.loader import ConfigService
from app.core.app_state import AppState
from app.engine.pipeline import ProcessingPipeline
from app.storage.database import DatabaseManager
from app.storage.repository import Repository
from app.telegram.client import TelethonClientService
from app.telegram.client_state import ClientStatus
from telethon.tl.types import Message

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

    # ── Init Telegram Client ──
    try:
        tg_config = state.config_service.raw.telegram
        state.telegram_client = TelethonClientService(
            session_file=str(DATA_DIR / "telegram" / "session.marketwatch"),
            api_id=int(os.getenv("TG_API_ID", "0")),
            api_hash=os.getenv("TG_API_HASH", ""),
            phone=os.getenv("TG_PHONE", ""),
            connect_timeout=tg_config.connect_timeout_seconds,
            request_timeout=tg_config.request_timeout_seconds,
            sequential_updates=tg_config.sequential_updates,
        )
        await state.telegram_client.start()
        state.telegram_connected = state.telegram_client.is_connected
        state.telegram_authorized = state.telegram_client.is_authorized
        if state.telegram_client.status == ClientStatus.AWAITING_CODE:
            await state.telegram_client.send_code()
        state.component_status["telegram"] = "ok"
    except Exception:
        state.component_status["telegram"] = "error"
        logger.exception("Failed to init Telegram client")

    # ── Init Alert Dispatcher ──
    if state.telegram_client and state.telegram_client.is_authorized:
        state.alert_dispatcher = AlertDispatcher(sender=state.telegram_client)
        state.component_status["alerts"] = "ok"

        # Wire pipeline into Telegram message handler
        if state.pipeline:
            # Build set of monitored chat peers for fast lookup
            monitored_peers = {
                mc.peer for mc in state.config_service.raw.telegram.monitored_chats
                if mc.enabled and mc.peer
            }

            async def handle_message(msg: Message, chat_peer: str) -> None:
                # Skip if not from a monitored chat
                if chat_peer not in monitored_peers:
                    return
                # Skip messages without text
                if not msg.text or not msg.text.strip():
                    return
                try:
                    result = await state.pipeline.process_message(
                        message_id=msg.id,
                        chat_id=chat_peer,
                        raw_text=msg.text or "",
                    )
                    state.messages_processed += 1
                    state.matches_total += result.match_count
                    if result.match_count > 0 and state.alert_dispatcher:
                        from app.engine.rules import RuleDecision
                        decisions = [RuleDecision(
                            rule_id=d.rule_id,
                            rule_title=d.rule_title or d.rule_id,
                            decision="MATCH" if d.is_match else "NOMATCH",
                            score=d.score,
                            threshold=d.threshold,
                        ) for d in result.decisions if d.is_match]
                        ok = await state.alert_dispatcher.dispatch_all(
                            decisions, result.raw_text, result.message_link
                        )
                        state.alerts_sent += sum(1 for o in ok if o)
                        state.alerts_failed += sum(1 for o in ok if not o)
                except Exception:
                    logger.exception("Failed to process message %s", msg.id)

            state.telegram_client.on_message = handle_message

        # ── Catch-up: process recent messages from monitored chats ──
        if state.pipeline and state.config_service.raw:
            catch_cfg = state.config_service.raw.catch_up
            if catch_cfg and catch_cfg.enabled:
                logger.info("Catch-up: processing recent messages from monitored chats")
                for mc in state.config_service.raw.telegram.monitored_chats:
                    if not mc.enabled or not mc.peer:
                        continue
                    try:
                        entity = await state.telegram_client._client.get_entity(mc.peer)
                        msgs = await state.telegram_client._client.get_messages(
                            entity, limit=catch_cfg.messages_per_chat_limit
                        )
                        count = 0
                        for msg in reversed(msgs):
                            if not msg.text:
                                continue
                            result = await state.pipeline.process_message(
                                message_id=msg.id,
                                chat_id=mc.peer,
                                raw_text=msg.text,
                            )
                            state.messages_processed += 1
                            state.matches_total += result.match_count
                            if result.match_count > 0 and state.alert_dispatcher:
                                from app.engine.rules import RuleDecision
                                decisions = [RuleDecision(
                                    rule_id=d.rule_id,
                                    rule_title=d.rule_title or d.rule_id,
                                    decision="MATCH" if d.is_match else "NOMATCH",
                                    score=d.score,
                                    threshold=d.threshold,
                                ) for d in result.decisions if d.is_match]
                                ok = await state.alert_dispatcher.dispatch_all(
                                    decisions, result.raw_text, result.message_link
                                )
                                state.alerts_sent += sum(1 for o in ok if o)
                                state.alerts_failed += sum(1 for o in ok if not o)
                            count += 1
                        logger.info("Catch-up: %s → %d messages processed", mc.peer, count)
                    except Exception:
                        logger.exception("Catch-up failed for %s", mc.peer)
    else:
        state.alert_dispatcher = AlertDispatcher()
        state.component_status["alerts"] = "pending_auth"
        logger.warning("Alert dispatcher created without sender (Telegram not authorized)")

    app.state.app_state = state
    state.component_status["app"] = "running"
    logger.info("tg-market-watch started")

    yield

    # ── Shutdown ──
    state.component_status["app"] = "stopped"
    if state.telegram_client:
        await state.telegram_client.stop()
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
