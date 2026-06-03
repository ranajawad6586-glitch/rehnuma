"""Persisted Rehnuma conversations (CLAUDE.md s.6 `ai_sessions`).

transcript is an ordered list of {"role": "user"|"assistant", "content": str}. provider_used
records which provider in the fallback chain served the most recent reply.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AiSession(Base):
    __tablename__ = "ai_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id"), index=True, nullable=True)

    transcript: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    provider_used: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
