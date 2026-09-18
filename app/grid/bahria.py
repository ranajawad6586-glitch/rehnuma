"""Reference plot grid for Bahria Town Rawalpindi/Islamabad.

The real possession register is not public, so this generates a plausible grid over the
society's **actual address space**. Two things are real here, and one is not:

- The addressing *shape* is real. Phases 1-7 are addressed "House 123, Street 45, Phase 4" —
  they have no block or sector layer (the postal service treats Phases 1-4 as a single area,
  46220). Only Phase 8 is subdivided, into lettered sectors plus named schemes, giving
  "House 12, Street 5, Umer Block, Phase 8".
- The Phase 8 sector and block names are real, taken from the society's phase maps.
- The street and house *numbers* are synthetic. A given real house may not be present. Only
  importing the genuine register fixes that.

Earlier revisions invented a block layer for every phase and numbered houses from a
phase-derived formula, so a resident's real address never matched.

Pure stdlib + deterministic — no third-party imports, no randomness — so it is fully
unit-testable without a database. Re-running yields byte-identical rows (idempotent seed).
"""
from __future__ import annotations

from dataclasses import dataclass

PHASES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)

# Only Phase 8 carries a sector/block layer; elsewhere the street is the subdivision.
AREA_PHASES: tuple[int, ...] = (8,)

_SAFARI_VALLEY = (
    "Abu Bakar Block", "Umer Block", "Usman Block", "Ali Block",
    "Rafi Block", "Khalid Block", "Awais Block",
)
_PHASE_8_SECTORS = (
    "Sector A", "Sector B", "Sector C", "Sector D",
    "Sector E-1", "Sector E-2", "Sector E-3", "Sector E-4",
    "Sector F-1", "Sector F-2", "Sector F-3", "Sector F-4",
    "Sector G", "Sector H", "Sector I", "Sector J",
    "Sector K", "Sector L", "Sector M", "Sector N", "Sector P",
)
_AWAMI_VILLAS = ("Awami Villas 1", "Awami Villas 2", "Awami Villas 3",
                 "Awami Villas 5", "Awami Villas 6")
_OTHER_SCHEMES = ("Overseas Enclave", "Bahria Orchard", "Rose Garden", "Bahria Heights")

# "" means the phase has no area layer — the address is just street + house number.
NO_AREA = ""

AREAS_BY_PHASE: dict[int, tuple[str, ...]] = {p: (NO_AREA,) for p in PHASES}
AREAS_BY_PHASE[8] = _PHASE_8_SECTORS + _SAFARI_VALLEY + _AWAMI_VILLAS + _OTHER_SCHEMES

# Every real area name, for validation and the owner form.
AREAS: tuple[str, ...] = tuple(
    dict.fromkeys(a for areas in AREAS_BY_PHASE.values() for a in areas if a)
)

# Phase 8's areas span three naming conventions; grouping keeps the picker scannable.
GROUPS_BY_PHASE: dict[int, tuple[tuple[str, tuple[str, ...]], ...]] = {
    p: () if p not in AREA_PHASES else (
        ("Sectors", _PHASE_8_SECTORS),
        ("Safari Valley", _SAFARI_VALLEY),
        ("Awami Villas", _AWAMI_VILLAS),
        ("Other schemes", _OTHER_SCHEMES),
    )
    for p in PHASES
}

# Plausible density. Phases 1-7 are whole phases, so they carry many more streets than a
# single Phase 8 sector does.
STREETS_PER_PHASE: int = 40
STREETS_PER_AREA: int = 8
HOUSES_PER_STREET: int = 40

# Plot categories actually marketed in Bahria Town. CLAUDE.md s.0 names 5-marla / 10-marla /
# 1-kanal as the standard trio; 7-marla (dominant in Safari Valley), 8-marla and 2-kanal are
# equally real and are accepted so owners are not forced to mis-declare.
HOUSE_SIZES: tuple[str, ...] = ("5-marla", "7-marla", "8-marla", "10-marla", "1-kanal", "2-kanal")

# Pakistan Post: Phases 1-4 share 46220; Phases 5-8 use 46620.
def postal_code(phase: int) -> str:
    return "46220" if phase <= 4 else "46620"


BAHRIA_CENTER: tuple[float, float] = (33.5286, 73.0879)
_PHASE_STEP = 0.012
_AREA_STEP = 0.004
_STREET_STEP = 0.0004
_HOUSE_STEP = 0.00008


@dataclass(frozen=True)
class GridPlot:
    phase: str          # e.g. "Phase 8"
    sector: str         # e.g. "Umer Block"; "" for phases with no area layer
    street: str         # e.g. "Street 13"
    house_ref: str      # the house number as written, e.g. "129"
    possession_ref: str
    size: str
    lat: float
    lng: float

    @property
    def address(self) -> str:
        """The address the way a resident writes it."""
        parts = [f"House {self.house_ref}", self.street]
        if self.sector:
            parts.append(self.sector)
        parts.append(self.phase)
        return ", ".join(parts)

    @property
    def wkt(self) -> str:
        """WKT point for PostGIS (lng lat order)."""
        return f"POINT({self.lng:.6f} {self.lat:.6f})"


def _slug(area: str) -> str:
    return area.upper().replace(" ", "-") if area else "NA"


def _size_for(phase: int, area: str, street: int, house: int) -> str:
    """Safari Valley is a documented 5/7-marla zone; elsewhere cycle the categories."""
    if area in _SAFARI_VALLEY:
        return ("5-marla", "7-marla")[house % 2]
    return HOUSE_SIZES[(phase + street + house) % len(HOUSE_SIZES)]


def streets_for(phase: int) -> int:
    return STREETS_PER_AREA if phase in AREA_PHASES else STREETS_PER_PHASE


def generate_grid() -> list[GridPlot]:
    """Generate the full Bahria reference grid, deterministically ordered."""
    plots: list[GridPlot] = []
    base_lat, base_lng = BAHRIA_CENTER
    for phase in PHASES:
        for a_idx, area in enumerate(AREAS_BY_PHASE[phase]):
            for s in range(streets_for(phase)):
                street_no = s + 1
                for h in range(HOUSES_PER_STREET):
                    house = h + 1          # house numbers restart on every street
                    plots.append(
                        GridPlot(
                            phase=f"Phase {phase}",
                            sector=area,
                            street=f"Street {street_no}",
                            house_ref=str(house),
                            possession_ref=(
                                f"BT-P{phase}-{_slug(area)}-S{street_no:03d}-{house:03d}"
                            ),
                            size=_size_for(phase, area, street_no, house),
                            lat=base_lat + phase * _PHASE_STEP + a_idx * _AREA_STEP
                            + s * _STREET_STEP + h * _HOUSE_STEP,
                            lng=base_lng + a_idx * _AREA_STEP - s * _STREET_STEP,
                        )
                    )
    return plots


def grid_size() -> int:
    """Expected number of plots, without generating them."""
    return sum(
        len(AREAS_BY_PHASE[p]) * streets_for(p) * HOUSES_PER_STREET for p in PHASES
    )
