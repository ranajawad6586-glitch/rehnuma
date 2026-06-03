"""Listing state-machine transitions — pure, runs anywhere with just pytest."""
from app.listings.status import ListingStatus as S
from app.listings.status import can_transition


def test_forward_chain():
    assert can_transition(S.DRAFT, S.PLOT_SUBMITTED)
    assert can_transition(S.PLOT_SUBMITTED, S.GRID_MATCHED)
    assert can_transition(S.GRID_MATCHED, S.OWNER_VERIFIED)
    assert can_transition(S.OWNER_VERIFIED, S.LIVE)
    assert can_transition(S.LIVE, S.RENTED)


def test_cannot_skip_to_live():
    # Rule 2: no jumping straight to LIVE without the verification chain.
    assert not can_transition(S.DRAFT, S.LIVE)
    assert not can_transition(S.GRID_MATCHED, S.LIVE)


def test_delist_from_any_active_state():
    for s in (S.DRAFT, S.PLOT_SUBMITTED, S.GRID_MATCHED, S.OWNER_VERIFIED, S.LIVE):
        assert can_transition(s, S.DELISTED)


def test_delisted_is_terminal():
    assert not can_transition(S.DELISTED, S.LIVE)
    assert not can_transition(S.DELISTED, S.GRID_MATCHED)


def test_relist_after_rented_or_expired():
    assert can_transition(S.RENTED, S.LIVE)
    assert can_transition(S.EXPIRED, S.LIVE)
