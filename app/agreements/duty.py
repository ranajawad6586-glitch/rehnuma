"""Stamp-duty band computation (CLAUDE.md s.3, rule 4).

Duty scales with ANNUAL rent — never a fixed Rs 200. Rs 200 paper genuinely suffices for many
short/low-rent informal agreements, but is not universal, so we always show the computed band.
Pure stdlib, unit-tested.

Bands (annual rent -> duty):
    <= 100,000          -> Rs 500
    100,001 - 500,000   -> Rs 1,000
    > 500,000           -> Rs 2,000
"""
from __future__ import annotations

from dataclasses import dataclass

MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class StampDuty:
    annual_rent: int
    duty: int
    label: str


def compute_stamp_duty(annual_rent: int) -> StampDuty:
    if annual_rent <= 100_000:
        duty, band = 500, "annual rent up to Rs 100,000"
    elif annual_rent <= 500_000:
        duty, band = 1_000, "annual rent Rs 100,001–500,000"
    else:
        duty, band = 2_000, "annual rent over Rs 500,000"
    return StampDuty(annual_rent=annual_rent, duty=duty, label=f"Rs {duty:,} ({band})")


def stamp_duty_for_monthly_rent(monthly_rent: int) -> StampDuty:
    return compute_stamp_duty(monthly_rent * MONTHS_PER_YEAR)
