"""Bahria Town address space: what counts as a well-formed address.

**This is a plausibility check, not a possession check.** Bahria Town's real plot register is
not public, so the app cannot confirm that a given house exists, let alone who owns it. An
earlier design pre-seeded a synthetic grid of every plot and matched against it, which
rejected essentially every genuine resident: the numbers were invented, so a real address like
"House 929, Street 41, Phase 3" was absent by construction.

So verification is split honestly:

- *This module* validates the shape and range of an address — a real phase, a sector only
  where sectors exist, and street/house numbers inside plausible bounds.
- Trust in the person comes from CNIC + phone OTP (M2), not from the address.

The bounds below are deliberately generous placeholders, sized so no plausible real address is
refused. They are not authoritative. Replace them with per-phase figures from someone who
knows the society (or the real register, if it is ever obtainable) — that is the only way this
check becomes meaningful rather than merely permissive.
"""
from __future__ import annotations

from dataclasses import dataclass

PHASES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)

# Only Phase 8 carries a sector/block layer. Phases 1-7 are addressed "House 123, Street 45,
# Phase 4" — Pakistan Post treats Phases 1-4 as one area (46220), with no block subdivision.
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

# "" means the phase has no sector layer.
NO_AREA = ""

AREAS_BY_PHASE: dict[int, tuple[str, ...]] = {p: (NO_AREA,) for p in PHASES}
AREAS_BY_PHASE[8] = _PHASE_8_SECTORS + _SAFARI_VALLEY + _AWAMI_VILLAS + _OTHER_SCHEMES

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


@dataclass(frozen=True)
class Bounds:
    """Highest plausible street and house number for a phase."""
    max_street: int
    max_house: int


# PLACEHOLDER bounds — generous on purpose so real addresses are not refused. Phase 8's
# sectors are individually smaller than a whole older phase, but the ceiling is kept high
# because residents also write whole-phase numbering.
_DEFAULT_BOUNDS = Bounds(max_street=150, max_house=3000)
BOUNDS_BY_PHASE: dict[int, Bounds] = {p: _DEFAULT_BOUNDS for p in PHASES}

# Plot categories actually marketed in Bahria Town. CLAUDE.md s.0 names 5-marla / 10-marla /
# 1-kanal as the standard trio; 7-marla (dominant in Safari Valley), 8-marla and 2-kanal are
# equally real and are accepted so owners are not forced to mis-declare.
HOUSE_SIZES: tuple[str, ...] = ("5-marla", "7-marla", "8-marla", "10-marla", "1-kanal", "2-kanal")


def postal_code(phase: int) -> str:
    """Pakistan Post: Phases 1-4 share 46220; Phases 5-8 use 46620."""
    return "46220" if phase <= 4 else "46620"


def format_address(phase: int, sector: str, street: str, house_ref: str) -> str:
    """The address the way a resident writes it (sector omitted where none exists)."""
    parts = [f"House {house_ref}", street]
    if sector:
        parts.append(sector)
    parts.append(f"Phase {phase}")
    return ", ".join(p for p in parts if p)


def check_address(phase: int, sector: str, street_no: int, house_no: int) -> str | None:
    """Return None if the address is plausible, else a reason the owner can act on."""
    if phase not in PHASES:
        return f"Phase {phase} is not part of Bahria Town; phases are {list(PHASES)}"

    allowed = tuple(a for a in AREAS_BY_PHASE[phase] if a)
    if phase in AREA_PHASES:
        if not sector:
            return f"Phase {phase} requires a sector, one of {list(allowed)}"
        if sector not in allowed:
            return f"Phase {phase} has no {sector!r}; its sectors are {list(allowed)}"
    elif sector:
        return f"Phase {phase} has no sectors — give only street and house number"

    bounds = BOUNDS_BY_PHASE[phase]
    if not 1 <= street_no <= bounds.max_street:
        return f"Street {street_no} looks wrong for Phase {phase} (expected 1-{bounds.max_street})"
    if not 1 <= house_no <= bounds.max_house:
        return f"House {house_no} looks wrong for Phase {phase} (expected 1-{bounds.max_house})"
    return None
