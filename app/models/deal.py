"""A deal between a tenant and a listing's owner (CLAUDE.md s.6 `deals`).

Contact privacy gate: each side records consent independently; the counter-party's phone is
revealed only when BOTH have consented. locked_terms is populated when an offer is ACCEPTED (M7).
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.deals.status import DealStatus
from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (UniqueConstraint("listing_id", "tenant_id", name="uq_deal_listing_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(24), default=DealStatus.INQUIRY.value, nullable=False)
    locked_terms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # set on ACCEPTED (M7)

    # Contact privacy gate (rule 7): both must consent before phones are revealed.
    tenant_consent_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_consent_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    @property
    def contact_shared(self) -> bool:
        return self.tenant_consent_contact and self.owner_consent_contact
