"""A structured offer within a deal's negotiation (CLAUDE.md s.5).

Offers are discrete fields, never free text. The counter loop is a sequence of offers; the
latest PENDING one is "on the table". On accept, its fields are copied into deals.locked_terms
and the agreement (M8) is generated only from those locked terms.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.deals.status import OfferStatus
from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), index=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    rent: Mapped[int] = mapped_column(Integer, nullable=False)            # PKR / month
    advance_months: Mapped[int] = mapped_column(Integer, nullable=False)  # months of advance
    security: Mapped[int] = mapped_column(Integer, nullable=False)        # PKR security deposit
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    move_in: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(16), default=OfferStatus.PENDING.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def as_terms(self) -> dict:
        """Serializable snapshot for deals.locked_terms / agreement generation."""
        return {
            "rent": self.rent,
            "advance_months": self.advance_months,
            "security": self.security,
            "duration_months": self.duration_months,
            "move_in": self.move_in.isoformat(),
        }
