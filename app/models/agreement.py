"""A generated tenancy agreement (CLAUDE.md s.6 `agreements`).

Generated ONLY from a deal's locked_terms (s.5). `terms` is the full snapshot used to render
the PDF (locked terms + computed duty + advisories); stamp_duty_band is the computed duty in PKR.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agreement(Base):
    __tablename__ = "agreements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), unique=True, index=True, nullable=False)
    terms: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stamp_duty_band: Mapped[int] = mapped_column(Integer, nullable=False)  # computed duty, PKR
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
