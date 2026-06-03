"""Normalize a raw Apify dataset item into RehnumaRent Listing fields.

Apify Actors return different shapes, so this is tolerant: it looks for a value across several
likely keys and parses messy text (e.g. "Rs 1.5 Lakh", "10 Marla", "Bahria Town Phase 8").
Pure stdlib + deterministic, so it's fully unit-testable without Apify or a DB.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# Bahria standardized categories the app filters on; others pass through (e.g. "7-marla").
_SIZE_RE = re.compile(r"([\d.]+)\s*(marla|kanal)", re.I)
_PHASE_RE = re.compile(r"phase\s*([1-8])", re.I)
_BLOCK_RE = re.compile(r"\b(?:block|sector)\s*([A-Za-z0-9]{1,6})", re.I)


def _first(item: dict, *keys: str) -> Any:
    for k in keys:
        v = item.get(k)
        if v not in (None, "", []):
            return v
    return None


def parse_rent(value: Any) -> int | None:
    """Parse a monthly rent. Handles plain numbers and 'Rs 1.5 Lakh' / '2 Crore' style text."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).lower().replace(",", "")
    num = re.search(r"[\d.]+", text)
    if not num:
        return None
    amount = float(num.group())
    if "crore" in text:
        amount *= 10_000_000
    elif "lac" in text or "lakh" in text:
        amount *= 100_000
    return int(amount)


def _size_from_text(text: Any) -> str | None:
    m = _SIZE_RE.search(str(text or ""))
    return f"{m.group(1)}-{m.group(2).lower()}" if m else None


def _size_from_sqft(area: Any, unit: Any) -> str | None:
    """Convert a numeric area in sqft to marla/kanal (1 marla = 225 sqft, 1 kanal = 20 marla)."""
    if not area or "sqft" not in str(unit or "").lower():
        return None
    try:
        marla = float(area) / 225.0
    except (TypeError, ValueError):
        return None
    if marla >= 20:
        return f"{round(marla / 20.0, 1):g}-kanal"
    return f"{round(marla, 1):g}-marla"


def parse_size(value: Any) -> str:
    return _size_from_text(value) or "5-marla"


def parse_area(location: Any) -> tuple[str, str]:
    """Return (phase, sector) fitted to the column widths (16 / 8)."""
    text = str(location or "")
    phase_m = _PHASE_RE.search(text)
    if phase_m:
        phase = f"Phase {phase_m.group(1)}"
    else:
        low = text.lower()
        if "chaklala" in low:
            phase = "Chaklala 3"
        elif "satellite" in low:
            phase = "Satellite Twn"
        elif "media town" in low:
            phase = "Media Town"
        elif "westridge" in low:
            phase = "Westridge"
        elif "bahria" in low and "height" in low:
            phase = "Bahria Hghts"
        else:
            # First meaningful chunk of the location, trimmed to fit.
            phase = (text.split(",")[0].strip() or "Rawalpindi")[:16]
    block_m = _BLOCK_RE.search(text)
    sector = (block_m.group(1) if block_m else "Main")[:8]
    return phase[:16], sector


_DEFAULT_BEDS = {"1-kanal": 5, "10-marla": 4, "7-marla": 3, "5-marla": 3}


def _default_beds(size: str) -> int:
    if size in _DEFAULT_BEDS:
        return _DEFAULT_BEDS[size]
    m = _SIZE_RE.search(size)
    if m and m.group(2).lower() == "kanal":
        return 5
    val = float(m.group(1)) if m else 5
    return 1 if val < 4 else 2 if val < 7 else 3 if val < 11 else 5


def normalize_item(item: dict) -> dict | None:
    """Map one Apify item -> Listing kwargs, or None if it lacks the essentials (rent + location)."""
    rent = parse_rent(_first(item, "rent", "price", "priceText", "monthly_rent", "amount"))
    location = _first(item, "location", "address", "area_location", "locality", "title")
    if not rent or rent <= 0 or not location:
        return None

    # Prefer a short stable id; fall back to a hash of the (often very long) URL so external_ref
    # stays within String(255).
    external = _first(item, "external_id", "externalId", "id", "url", "link")
    if not external:
        return None
    ext = str(external)
    if len(ext) > 180:
        ext = hashlib.sha1(ext.encode()).hexdigest()

    # Size: the title usually names it ("2.5 Kanal"); else a marla/kanal text field; else
    # convert a numeric sqft area; else a safe default.
    size = (
        _size_from_text(item.get("title"))
        or _size_from_text(_first(item, "area", "size", "areaText", "land_area"))
        or _size_from_sqft(item.get("area"), item.get("area_unit"))
        or "5-marla"
    )
    phase, sector = parse_area(location)
    beds = _first(item, "bedrooms", "beds", "bedroom", "rooms")
    baths = _first(item, "bathrooms", "baths", "bathroom")
    beds = int(beds) if isinstance(beds, (int, float)) or str(beds or "").isdigit() else _default_beds(size)
    baths = int(baths) if isinstance(baths, (int, float)) or str(baths or "").isdigit() else beds

    # Real listing photos, if the actor provides them (we deliberately ignore scraped agent
    # phone/agency — rule 7, dealer-free).
    raw_photos = item.get("photos") or item.get("images") or []
    photos = [p for p in raw_photos if isinstance(p, str)][:6] if isinstance(raw_photos, list) else []

    # Stable, human-ish house_ref derived from the source id.
    ref_seed = re.sub(r"\W+", "", ext)[-8:] or "0000"
    return {
        "external_ref": f"apify:{ext}",
        "phase": phase,
        "sector": sector,
        "house_ref": f"IMP-{ref_seed}"[:32],
        "size": size,
        "rent": rent,
        "beds": beds,
        "baths": baths,
        "photos": photos,
    }
