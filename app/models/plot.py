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
        UniqueConstraint("phase", "sector", "house_ref", name="uq_plot_phase_sector_house"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phase: Mapped[str] = mapped_column(String(16), index=True)
    # Real block names are long ("Overseas Enclave", "Abu Bakar Block"), not single letters.
    sector: Mapped[str] = mapped_column(String(64), index=True)
    house_ref: Mapped[str] = mapped_column(String(32), index=True)
    # Street the house sits on, e.g. "Street 13". Informational: house numbers are unique
    # within a block, so the match key stays {phase, sector, house_ref}.
    street: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Possession reference seeded with the grid; used to confirm a real plot exists.
    possession_ref: Mapped[str] = mapped_column(String(64))
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Plot {self.phase}/{self.sector}/{self.house_ref}>"
