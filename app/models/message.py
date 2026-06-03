"""A message within a deal's chat (CLAUDE.md s.6 `messages`).

type is text | offer | system. system messages have no human sender (sender_id NULL).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.deals.status import MessageType
from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), index=True, nullable=False)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # NULL = system
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(16), default=MessageType.TEXT.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
