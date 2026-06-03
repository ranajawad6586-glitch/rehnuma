"""Deterministic generator for the Bahria Town Islamabad reference plot grid.

MVP scope is Bahria ISB only (CLAUDE.md s.0). The real possession registry is not
available, so this produces a *structured synthetic* grid over the known address space:
phases 1-8, sectors A-F, numbered houses. The shape (phase/sector/house_ref) is what
listing verification matches against; coordinates are plausible points clustered around
Bahria Town ISB for future PostGIS queries.

Pure stdlib + deterministic — no third-party imports, no randomness — so it is fully
unit-testable without a database. Re-running yields byte-identical rows (idempotent seed).
"""
from __future__ import annotations

from dataclasses import dataclass

# Known address space. Encoded as config per CLAUDE.md s.3 (no scattered magic numbers).
PHASES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
SECTORS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
HOUSES_PER_SECTOR: int = 40  # synthetic grid density per sector

# Standardized Bahria house categories (CLAUDE.md s.0), cycled deterministically.
HOUSE_SIZES: tuple[str, ...] = ("5-marla", "10-marla", "1-kanal")

# Approx center of Bahria Town Islamabad (lat, lng) and per-index spread in degrees.
BAHRIA_CENTER: tuple[float, float] = (33.5286, 73.0879)
_PHASE_STEP = 0.012
_SECTOR_STEP = 0.004
_HOUSE_STEP = 0.0002


@dataclass(frozen=True)
class GridPlot:
    phase: str          # e.g. "Phase 4"
    sector: str         # e.g. "C"
    house_ref: str      # e.g. "287-C"
    possession_ref: str # e.g. "BT-ISB-P4-C-0287"
    size: str           # one of HOUSE_SIZES
    lat: float
    lng: float

    @property
    def wkt(self) -> str:
        """WKT point for PostGIS (lng lat order)."""
        return f"POINT({self.lng:.6f} {self.lat:.6f})"


def _house_number(phase: int, sector_idx: int, house_idx: int) -> int:
    """Stable, human-plausible house number unique within a sector."""
    return phase * 100 + sector_idx * 40 + (house_idx + 1)


def generate_grid() -> list[GridPlot]:
    """Generate the full Bahria ISB reference grid, deterministically ordered."""
    plots: list[GridPlot] = []
    base_lat, base_lng = BAHRIA_CENTER
    for phase in PHASES:
        for s_idx, sector in enumerate(SECTORS):
            for h in range(HOUSES_PER_SECTOR):
                num = _house_number(phase, s_idx, h)
                house_ref = f"{num}-{sector}"
                possession_ref = f"BT-ISB-P{phase}-{sector}-{num:04d}"
                size = HOUSE_SIZES[(num) % len(HOUSE_SIZES)]
                lat = base_lat + phase * _PHASE_STEP + s_idx * _SECTOR_STEP + h * _HOUSE_STEP
                lng = base_lng + phase * _PHASE_STEP + s_idx * _SECTOR_STEP + h * _HOUSE_STEP
                plots.append(
                    GridPlot(
                        phase=f"Phase {phase}",
                        sector=sector,
                        house_ref=house_ref,
                        possession_ref=possession_ref,
                        size=size,
                        lat=round(lat, 6),
                        lng=round(lng, 6),
                    )
                )
    return plots


def grid_size() -> int:
    return len(PHASES) * len(SECTORS) * HOUSES_PER_SECTOR
