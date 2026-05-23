"""SQLAlchemy ORM models for tg-market-watch."""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MessageOrm(Base):
    """Raw (or first-normalized) message from Telegram."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_peer: Mapped[str] = mapped_column(String(128), nullable=False)
    chat_title: Mapped[str] = mapped_column(String(256), default="")
    sender_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    text_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    normalized_hash: Mapped[str] = mapped_column(String(64), index=True, default="")

    matches = relationship("MatchOrm", back_populates="message", cascade="all, delete-orphan")


class MatchOrm(Base):
    """Rule match decision for a message."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rule_title: Mapped[str] = mapped_column(String(256), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    decision: Mapped[str] = mapped_column(String(32), default="MATCH")
    config_hash: Mapped[str] = mapped_column(String(64), default="")
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    message = relationship("MessageOrm", back_populates="matches")


class AlertOrm(Base):
    """Alerts sent to users."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="sent")  # sent, failed
    sent_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
