"""The offer-builder "Fair?" check (CLAUDE.md s.4).

Compares proposed numbers to the asking rent and Bahria norms, returning a one-line verdict
plus structured flags. Deterministic and pure — this is the reliable in-app verdict; the
Rehnuma chat (/ai/ask) can elaborate conversationally. Encodes the norms from CLAUDE.md s.3:
advance 2–3 months + 1 month security is normal; **6 months advance is a red flag**.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ADVANCE_NORM_MAX = 3       # months; 2–3 is normal
ADVANCE_RED_FLAG = 6       # months; >= this is a red flag Rehnuma must surface
DEFAULT_TERM_MONTHS = 12


@dataclass
class Fairness:
    verdict: str
    is_fair: bool
    flags: list[str] = field(default_factory=list)


def evaluate_fairness(
    asking_rent: int,
    rent: int,
    advance_months: int,
    security: int,
    duration_months: int = DEFAULT_TERM_MONTHS,
) -> Fairness:
    flags: list[str] = []
    is_fair = True

    # --- Advance vs norm (the load-bearing red flag) ---
    if advance_months >= ADVANCE_RED_FLAG:
        flags.append(f"**{advance_months} months advance** is a red flag — Bahria norm is 2–3 months")
        is_fair = False
    elif advance_months > ADVANCE_NORM_MAX:
        flags.append(f"advance of **{advance_months} months** is above the usual 2–3")

    # --- Rent vs asking ---
    if asking_rent > 0:
        diff_pct = round((rent - asking_rent) / asking_rent * 100)
        if diff_pct <= -1:
            rent_note = f"rent **Rs {rent:,}** is {abs(diff_pct)}% below asking"
        elif diff_pct >= 1:
            rent_note = f"rent **Rs {rent:,}** is {diff_pct}% above asking"
            flags.append(rent_note)
        else:
            rent_note = f"rent **Rs {rent:,}** is at asking"
    else:
        rent_note = f"rent **Rs {rent:,}**"

    # --- Security vs ~1 month ---
    if rent > 0 and security > rent:
        flags.append(f"security **Rs {security:,}** exceeds one month's rent")
    elif security == 0:
        flags.append("no security deposit")

    # --- Term ---
    if duration_months < DEFAULT_TERM_MONTHS:
        flags.append(f"{duration_months}-month term is shorter than the usual 12")

    # --- One-line verdict ---
    if is_fair and not flags:
        verdict = (
            f"Looks fair: {rent_note}, advance **{advance_months} months** + "
            f"security **Rs {security:,}** are within Bahria norms."
        )
    elif is_fair:
        verdict = f"Mostly fair — {rent_note}. Note: " + "; ".join(flags) + "."
    else:
        verdict = "Caution — " + "; ".join(flags) + "."

    return Fairness(verdict=verdict, is_fair=is_fair, flags=flags)
