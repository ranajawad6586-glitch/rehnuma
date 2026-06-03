"""Legal advisories for a generated agreement (CLAUDE.md s.3, rule 4).

Every line is hedged — we NEVER assert a fixed legal certainty. Requirements vary by
jurisdiction (ICT vs Punjab) and change over time; the app surfaces them as things to verify.
Pure stdlib, unit-tested.
"""
from __future__ import annotations

DEFAULT_TERM_MONTHS = 12


def build_advisories(duration_months: int) -> list[str]:
    advisories = [
        "Stamp duty scales with the annual rent — the band shown is computed, not a flat "
        "Rs 200. Rs 200 paper is common for short or low-rent informal agreements but is not "
        "universally correct.",
    ]
    if duration_months >= DEFAULT_TERM_MONTHS:
        advisories.append(
            "For a 12-month (or longer) term, ICT/Punjab may require e-stamping rather than "
            "plain stamp paper. Confirm the current requirement before signing."
        )
    advisories.append(
        "Registration with the rent registrar may be required (e.g. under the Punjab Rented "
        "Premises Act). Requirements vary by jurisdiction — verify locally."
    )
    advisories.append(
        "Police tenant verification is required. Generate the verification form and submit it "
        "to the local police station."
    )
    advisories.append("Clear all Bahria Town maintenance dues before possession is handed over.")
    return advisories
