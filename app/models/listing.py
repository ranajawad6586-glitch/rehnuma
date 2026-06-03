"""A rental listing. Goes LIVE only after Bahria grid match AND owner CNIC+OTP (rule 2)."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.listings.status import ListingStatus
from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    # Set once the submitted {phase, sector, house_ref} matches the seeded grid.
    plot_id: Mapped[int | None] = mapped_column(ForeignKey("plots.id"), index=True, nullable=True)

    # Address as submitted (kept for the record even before/after the plot match).
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    sector: Mapped[str] = mapped_column(String(8), nullable=False)
    house_ref: Mapped[str] = mapped_column(String(32), nullable=False)

    size: Mapped[str] = mapped_column(String(16), nullable=False)  # 5-marla | 10-marla | 1-kanal
    rent: Mapped[int] = mapped_column(Integer, nullable=False)     # PKR / month
    beds: Mapped[int] = mapped_column(Integer, nullable=False)
    baths: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=ListingStatus.DRAFT.value, nullable=False, index=True)
    photos: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Source key for externally-imported listings (e.g. "apify:<url>"); NULL for native ones.
    # Unique so re-running an import is idempotent.
    external_ref: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
