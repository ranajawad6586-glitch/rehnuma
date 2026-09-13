"""Reference plot grid for Bahria Town Rawalpindi/Islamabad.

The real possession register is not public, so this generates a plausible grid over the
society's **actual documented address space** — the real phases and the real block/sector
names — rather than an invented one. Two consequences worth being explicit about:

- The block and sector names below are real (sourced from Bahria Town's own phase maps and
  the major property portals), so an owner picking their block will find it in the list.
- The *house numbers* within each block are still synthetic. A given real house may therefore
  not be present. Only importing the genuine register fixes that; see `DEPLOY-CLOUDFLARE.md`.

Addressing follows the convention actually used in the society, e.g.
"House 129, Street 13, Umer Block, Phase 8" — house numbers restart at 1 in each block, and
streets group roughly ten houses. Earlier revisions used a composite ref like "287-C" and
numbered houses from a phase-derived formula, which matched nothing anyone would ever type.

Pure stdlib + deterministic — no third-party imports, no randomness — so it is fully
unit-testable without a database. Re-running yields byte-identical rows (idempotent seed).
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Real address space ----------------------------------------------------
# Phases 1-6 sit together off the GT Road and are laid out in lettered blocks. Phase 7 and
# Phase 8 are the newer, larger extensions; Phase 8 additionally carries named sub-schemes
# (Safari Valley's blocks, Awami Villas, the Overseas Enclave) that residents use as the
# address, not a letter.
_LETTER_BLOCKS = ("Block A", "Block B", "Block C", "Block D", "Block E", "Block F")

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
_PHASE_8_NAMED = (
    "Awami Villas 1", "Awami Villas 2", "Awami Villas 3",
    "Awami Villas 5", "Awami Villas 6",
    "Overseas Enclave", "Bahria Orchard", "Rose Garden", "Bahria Heights",
)

PHASES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)

BLOCKS_BY_PHASE: dict[int, tuple[str, ...]] = {
    1: _LETTER_BLOCKS,
    2: _LETTER_BLOCKS,
    3: _LETTER_BLOCKS,
    4: _LETTER_BLOCKS,
    5: _LETTER_BLOCKS,
    6: ("Block A", "Block B", "Block C"),   # Phase 6 is the smallest of the older phases
    7: _LETTER_BLOCKS,
    8: _PHASE_8_SECTORS + _SAFARI_VALLEY + _PHASE_8_NAMED,
}

# Every distinct block name, for validation and for the owner form's dropdown.
SECTORS: tuple[str, ...] = tuple(
    dict.fromkeys(b for blocks in BLOCKS_BY_PHASE.values() for b in blocks)
)

HOUSES_PER_BLOCK: int = 150   # plausible density; real blocks run to a few hundred
HOUSES_PER_STREET: int = 10

# Plot categories actually marketed in Bahria Town. CLAUDE.md s.0 names 5-marla / 10-marla /
# 1-kanal as the standard trio; 7-marla (dominant in Safari Valley), 8-marla and 2-kanal are
# equally real and are accepted so owners are not forced to mis-declare.
HOUSE_SIZES: tuple[str, ...] = ("5-marla", "7-marla", "8-marla", "10-marla", "1-kanal", "2-kanal")

# Approx center of Bahria Town (lat, lng) and per-index spread in degrees.
BAHRIA_CENTER: tuple[float, float] = (33.5286, 73.0879)
_PHASE_STEP = 0.012
_BLOCK_STEP = 0.004
_HOUSE_STEP = 0.0002


@dataclass(frozen=True)
class GridPlot:
    phase: str          # e.g. "Phase 8"
    sector: str         # e.g. "Umer Block" / "Sector E-1" / "Block C"
    house_ref: str      # the house number as written, e.g. "129"
    street: str         # e.g. "Street 13"
    possession_ref: str # e.g. "BT-P8-UMER-BLOCK-0129"
    size: str           # one of HOUSE_SIZES
    lat: float
    lng: float

    @property
    def address(self) -> str:
        """The address the way a resident writes it."""
        return f"House {self.house_ref}, {self.street}, {self.sector}, {self.phase}"

    @property
    def wkt(self) -> str:
        """WKT point for PostGIS (lng lat order)."""
        return f"POINT({self.lng:.6f} {self.lat:.6f})"


def _slug(block: str) -> str:
    return block.upper().replace(" ", "-")


def _size_for(phase: int, block: str, house: int) -> str:
    """Assign a plausible category: Safari Valley is 5/7-marla, elsewhere cycle the rest."""
    if block in _SAFARI_VALLEY:
        return ("5-marla", "7-marla")[house % 2]
    return HOUSE_SIZES[(phase + house) % len(HOUSE_SIZES)]


def generate_grid() -> list[GridPlot]:
    """Generate the full Bahria reference grid, deterministically ordered."""
    plots: list[GridPlot] = []
    base_lat, base_lng = BAHRIA_CENTER
    for phase in PHASES:
        for b_idx, block in enumerate(BLOCKS_BY_PHASE[phase]):
            for h in range(HOUSES_PER_BLOCK):
                house = h + 1                       # real blocks number from 1
                street = h // HOUSES_PER_STREET + 1
                plots.append(
                    GridPlot(
                        phase=f"Phase {phase}",
                        sector=block,
                        house_ref=str(house),
                        street=f"Street {street}",
                        possession_ref=f"BT-P{phase}-{_slug(block)}-{house:04d}",
                        size=_size_for(phase, block, house),
                        lat=base_lat + phase * _PHASE_STEP + b_idx * _BLOCK_STEP + h * _HOUSE_STEP,
                        lng=base_lng + b_idx * _BLOCK_STEP - h * _HOUSE_STEP,
                    )
                )
    return plots


def grid_size() -> int:
    """Expected number of plots, without generating them."""
    return sum(len(blocks) for blocks in BLOCKS_BY_PHASE.values()) * HOUSES_PER_BLOCK
