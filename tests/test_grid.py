"""Unit tests for the Bahria grid generator.

Pure stdlib — no DB, no FastAPI, no third-party imports — so these run on any Python 3.9+
with just pytest installed.
"""
import re

from app.grid.bahria import (
    AREA_PHASES,
    AREAS,
    AREAS_BY_PHASE,
    GROUPS_BY_PHASE,
    HOUSES_PER_STREET,
    HOUSE_SIZES,
    PHASES,
    generate_grid,
    grid_size,
    postal_code,
    streets_for,
)

SAFARI_VALLEY = {"Abu Bakar Block", "Umer Block", "Usman Block", "Ali Block",
                 "Rafi Block", "Khalid Block", "Awais Block"}


def test_grid_size_matches_address_space():
    assert len(generate_grid()) == grid_size()


def test_only_phase_8_has_an_area_layer():
    # Phases 1-7 are addressed "House 123, Street 45, Phase 4" — no block or sector exists.
    assert AREA_PHASES == (8,)
    for phase in PHASES:
        areas = [a for a in AREAS_BY_PHASE[phase] if a]
        assert bool(areas) == (phase in AREA_PHASES), phase


def test_phases_without_areas_use_an_empty_sector_not_null():
    # "" keeps the unique constraint working; Postgres treats NULLs as distinct.
    for p in generate_grid():
        if p.phase != "Phase 8":
            assert p.sector == ""


def test_real_phase_8_areas_are_present():
    p8 = set(AREAS_BY_PHASE[8])
    for name in ("Umer Block", "Ali Block", "Abu Bakar Block", "Overseas Enclave",
                 "Awami Villas 2", "Sector E-1", "Sector P"):
        assert name in p8, name


def test_plot_identity_is_unique():
    grid = generate_grid()
    keys = {(p.phase, p.sector, p.street, p.house_ref) for p in grid}
    assert len(keys) == len(grid), "phase/sector/street/house_ref must be unique"
    assert len({p.possession_ref for p in grid}) == len(grid)


def test_house_numbers_restart_on_every_street():
    grid = generate_grid()
    for p in grid:
        assert p.house_ref.isdigit()
        assert 1 <= int(p.house_ref) <= HOUSES_PER_STREET

    sample = [p for p in grid if p.phase == "Phase 4" and p.street == "Street 7"]
    assert sorted(int(p.house_ref) for p in sample) == list(range(1, HOUSES_PER_STREET + 1))


def test_street_numbering_is_well_formed_and_sized_per_phase():
    grid = generate_grid()
    for p in grid:
        assert re.fullmatch(r"Street \d+", p.street), p.street
    p4 = {p.street for p in grid if p.phase == "Phase 4"}
    p8 = {p.street for p in grid if p.sector == "Umer Block"}
    assert len(p4) == streets_for(4)
    assert len(p8) == streets_for(8)
    assert len(p4) > len(p8), "a whole phase has more streets than one Phase 8 sector"


def test_address_reads_the_way_a_resident_writes_it():
    grid = generate_grid()
    plain = next(p for p in grid if p.phase == "Phase 4")
    assert plain.address == f"House {plain.house_ref}, {plain.street}, Phase 4"

    sectored = next(p for p in grid if p.sector == "Umer Block")
    assert sectored.address == (
        f"House {sectored.house_ref}, {sectored.street}, Umer Block, Phase 8"
    )


def test_postal_codes_match_pakistan_post():
    assert {postal_code(p) for p in (1, 2, 3, 4)} == {"46220"}
    assert {postal_code(p) for p in (5, 6, 7, 8)} == {"46620"}


def test_sizes_are_real_bahria_categories():
    valid = set(HOUSE_SIZES)
    assert {"5-marla", "10-marla", "1-kanal"} <= valid
    assert all(p.size in valid for p in generate_grid())


def test_safari_valley_is_five_or_seven_marla():
    plots = [p for p in generate_grid() if p.sector in SAFARI_VALLEY]
    assert plots
    assert {p.size for p in plots} == {"5-marla", "7-marla"}


def test_groups_cover_phase_8_areas_exactly_once():
    grouped = [a for _, group in GROUPS_BY_PHASE[8] for a in group]
    assert sorted(grouped) == sorted(AREAS_BY_PHASE[8])
    assert len(grouped) == len(set(grouped))


def test_phases_without_areas_have_no_groups():
    for phase in PHASES:
        if phase not in AREA_PHASES:
            assert GROUPS_BY_PHASE[phase] == ()


def test_areas_is_the_deduplicated_union_of_real_area_names():
    union = {a for areas in AREAS_BY_PHASE.values() for a in areas if a}
    assert set(AREAS) == union


def test_generation_is_deterministic():
    assert generate_grid() == generate_grid()


def test_coordinates_near_bahria():
    for p in generate_grid():
        assert 33.4 <= p.lat <= 33.9
        assert 72.9 <= p.lng <= 73.4


def test_wkt_is_lng_lat_order():
    p = generate_grid()[0]
    lng_s, lat_s = p.wkt[len("POINT(") : -1].split(" ")
    assert float(lng_s) == round(p.lng, 6)
    assert float(lat_s) == round(p.lat, 6)
