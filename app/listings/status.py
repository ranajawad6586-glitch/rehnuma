"""Listing lifecycle state machine (CLAUDE.md s.5).

DRAFT -> PLOT_SUBMITTED -> GRID_MATCHED -> OWNER_VERIFIED -> LIVE -> (RENTED | EXPIRED | DELISTED)

Tenants only ever see LIVE (enforced in the router). Pure — no infra — so the transition
rules are unit-testable on their own.
"""
from __future__ import annotations

from enum import Enum


class ListingStatus(str, Enum):
    DRAFT = "DRAFT"
    PLOT_SUBMITTED = "PLOT_SUBMITTED"
    GRID_MATCHED = "GRID_MATCHED"
    OWNER_VERIFIED = "OWNER_VERIFIED"
    LIVE = "LIVE"
    RENTED = "RENTED"
    EXPIRED = "EXPIRED"
    DELISTED = "DELISTED"


# Allowed forward transitions. DELISTED is reachable from any active state (owner pulls it);
# RENTED/EXPIRED listings can be re-listed back to LIVE.
_ALLOWED: dict[ListingStatus, set[ListingStatus]] = {
    ListingStatus.DRAFT: {ListingStatus.PLOT_SUBMITTED, ListingStatus.DELISTED},
    ListingStatus.PLOT_SUBMITTED: {ListingStatus.GRID_MATCHED, ListingStatus.DELISTED},
    ListingStatus.GRID_MATCHED: {ListingStatus.OWNER_VERIFIED, ListingStatus.DELISTED},
    ListingStatus.OWNER_VERIFIED: {ListingStatus.LIVE, ListingStatus.DELISTED},
    ListingStatus.LIVE: {ListingStatus.RENTED, ListingStatus.EXPIRED, ListingStatus.DELISTED},
    ListingStatus.RENTED: {ListingStatus.LIVE, ListingStatus.DELISTED},
    ListingStatus.EXPIRED: {ListingStatus.LIVE, ListingStatus.DELISTED},
    ListingStatus.DELISTED: set(),
}


def can_transition(current: ListingStatus, target: ListingStatus) -> bool:
    return target in _ALLOWED.get(current, set())
