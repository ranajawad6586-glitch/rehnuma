"""User records. Phone and CNIC are stored ONLY as keyed hashes (CLAUDE.md rule 7) —
never the raw values. A user may be both owner and tenant (role flags).
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # HMAC-SHA256 hashes (see app.security). Unique => one account per phone/CNIC.
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    cnic_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    # Phone (E.164) Fernet-encrypted at rest (app.security). Sensitive — decrypted and exposed
    # ONLY to the counter-party after BOTH sides consent to share contact (rule 7). Never in any
    # UserOut. The column holds a Fernet token, hence the width.
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Role flags — a user can be both.
    can_own: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_rent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Set when phone OTP is cleared. CNIC capture is tracked by cnic_hash presence.
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    @property
    def phone_verified(self) -> bool:
        return self.verified_at is not None

    @property
    def cnic_captured(self) -> bool:
        return self.cnic_hash is not None

    @property
    def roles(self) -> list[str]:
        out = []
        if self.can_own:
            out.append("owner")
        if self.can_rent:
            out.append("tenant")
        return out
