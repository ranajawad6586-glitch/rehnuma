"""Normalization/validation for Pakistani phone numbers and CNICs.

Pure stdlib + deterministic so it is fully unit-testable without infra. Normalization is
required *before* hashing — two spellings of the same number must hash identically, or the
match/unique guarantees in CLAUDE.md rule 7 break.
"""
from __future__ import annotations

import re


class InvalidPhone(ValueError):
    pass


class InvalidCnic(ValueError):
    pass


def normalize_pk_phone(raw: str) -> str:
    """Normalize a Pakistani mobile number to E.164 (+923XXXXXXXXX).

    Accepts 03001234567, 3001234567, +923001234567, 00923001234567, with spaces/dashes.
    Raises InvalidPhone otherwise. PK mobiles are +92 then a 10-digit subscriber number
    beginning with 3.
    """
    if not raw or not raw.strip():
        raise InvalidPhone("phone is empty")

    digits = re.sub(r"\D", "", raw)

    # Strip international prefixes down to the 10-digit subscriber part (3XXXXXXXXX).
    if digits.startswith("0092"):
        digits = digits[4:]
    elif digits.startswith("92") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    if len(digits) != 10 or not digits.startswith("3"):
        raise InvalidPhone(f"not a valid Pakistani mobile number: {raw!r}")

    return "+92" + digits


_CNIC_RE = re.compile(r"^\d{13}$")


def normalize_cnic(raw: str) -> str:
    """Return the 13 digits of a Pakistani CNIC (no separators). Raises InvalidCnic.

    CNICs are 13 digits, commonly written #####-#######-#. We store the bare digits as the
    canonical form to hash.
    """
    if not raw:
        raise InvalidCnic("cnic is empty")
    digits = re.sub(r"\D", "", raw)
    if not _CNIC_RE.match(digits):
        raise InvalidCnic("CNIC must be 13 digits (e.g. 61101-1234567-1)")
    return digits


def format_cnic(digits: str) -> str:
    """Pretty-print a 13-digit CNIC as #####-#######-# (display only; never stored raw)."""
    digits = normalize_cnic(digits)
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
