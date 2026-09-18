"""The Bahria Town ISB reference plot grid.

This is the seeded address space that listing verification (M3) matches owner-submitted
{phase, sector, house_ref} against. lat/lng are plain coordinates (no PostGIS needed — the MVP
matches by reference, not spatially; revisit if real geo queries are added).
"""
from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Plot(Base):
    __tablename__ = "plots"
    __table_args__ = (
        # Street is part of the identity: house numbers restart on each street, so
        # {phase, sector, house_ref} alone is not unique.
        UniqueConstraint("phase", "sector", "street", "house_ref",
                         name="uq_plot_phase_sector_street_house"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phase: Mapped[str] = mapped_column(String(16), index=True)
    # Area/block name, e.g. "Umer Block". Empty string for Phases 1-7, which have no area
    # layer at all — "" rather than NULL so the unique constraint still bites (Postgres
    # treats NULLs as distinct).
    sector: Mapped[str] = mapped_column(String(64), index=True, default="")
    # Street the house sits on, e.g. "Street 13". Part of the address, not decoration.
    street: Mapped[str] = mapped_column(String(32), index=True, default="")
    house_ref: Mapped[str] = mapped_column(String(32), index=True)
    # Only fillable from a real possession register, which the MVP does not have.
    possession_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    @property
    def address(self) -> str:
        """The address the way a resident writes it (sector omitted where none exists)."""
        parts = [f"House {self.house_ref}", self.street]
        if self.sector:
            parts.append(self.sector)
        parts.append(self.phase)
        return ", ".join(p for p in parts if p)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Plot {self.phase}/{self.sector or '-'}/{self.street}/{self.house_ref}>"
