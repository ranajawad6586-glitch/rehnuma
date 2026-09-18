"""Address plausibility — the check that replaced the invented plot grid.

Pure stdlib, so these run without the app's Python 3.11 dependencies.
"""
import pytest

from app.grid.bahria import (
    AREA_PHASES,
    AREAS_BY_PHASE,
    BOUNDS_BY_PHASE,
    PHASES,
    check_address,
    format_address,
    postal_code,
)


def test_a_real_resident_address_is_accepted():
    # The address that the old synthetic grid rejected: house numbers there stopped at 40.
    assert check_address(3, "", 41, 929) is None


def test_generous_bounds_accept_large_real_numbers():
    for phase in PHASES:
        sector = AREAS_BY_PHASE[phase][0] if phase in AREA_PHASES else ""
        assert check_address(phase, sector, 100, 2500) is None, phase


@pytest.mark.parametrize("street,house", [(0, 5), (-1, 5), (5, 0), (5, -3)])
def test_zero_and_negative_numbers_are_rejected(street, house):
    assert check_address(3, "", street, house) is not None


def test_numbers_above_the_bound_are_rejected_with_the_range():
    b = BOUNDS_BY_PHASE[3]
    msg = check_address(3, "", b.max_street + 1, 10)
    assert msg and f"1-{b.max_street}" in msg
    msg = check_address(3, "", 10, b.max_house + 1)
    assert msg and f"1-{b.max_house}" in msg


def test_unknown_phase_is_rejected():
    assert check_address(99, "", 1, 1) is not None


def test_sector_is_required_in_phase_8_only():
    assert check_address(8, "", 4, 12) is not None
    assert check_address(8, "Umer Block", 4, 12) is None


def test_sector_is_refused_where_no_sector_layer_exists():
    msg = check_address(3, "Umer Block", 41, 929)
    assert msg and "no sectors" in msg


def test_sector_must_belong_to_the_phase():
    msg = check_address(8, "Nowhere Block", 4, 12)
    assert msg and "has no" in msg


def test_address_formatting_omits_an_absent_sector():
    assert format_address(3, "", "Street 41", "929") == "House 929, Street 41, Phase 3"
    assert format_address(8, "Umer Block", "Street 7", "412") == (
        "House 412, Street 7, Umer Block, Phase 8"
    )


def test_postal_codes_match_pakistan_post():
    assert {postal_code(p) for p in (1, 2, 3, 4)} == {"46220"}
    assert {postal_code(p) for p in (5, 6, 7, 8)} == {"46620"}
