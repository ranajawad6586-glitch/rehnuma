"""The Bahria Town ISB reference plot grid.

This is the seeded address space that listing verification (M3) matches owner-submitted
{phase, sector, house_ref} against. `geom` is a PostGIS point for future spatial queries.
"""
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Plot(Base):
    __tablename__ = "plots"
    __table_args__ = (
        UniqueConstraint("phase", "sector", "house_ref", name="uq_plot_phase_sector_house"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phase: Mapped[str] = mapped_column(String(16), index=True)
    sector: Mapped[str] = mapped_column(String(8), index=True)
    house_ref: Mapped[str] = mapped_column(String(32), index=True)
    # Possession reference seeded with the grid; used to confirm a real plot exists.
    possession_ref: Mapped[str] = mapped_column(String(64))
    geom: Mapped[WKBElement] = mapped_column(Geometry(geometry_type="POINT", srid=4326))

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Plot {self.phase}/{self.sector}/{self.house_ref}>"
