"""Unit tests for the Bahria grid generator.

Pure stdlib — no DB, no FastAPI, no third-party imports — so these run on any Python 3.9+
with just pytest installed. They are the runnable verification for M1's seed logic.
"""
import re

from app.grid.bahria import (
    BLOCKS_BY_PHASE,
    HOUSES_PER_BLOCK,
    HOUSES_PER_STREET,
    HOUSE_SIZES,
    PHASES,
    SECTORS,
    generate_grid,
    grid_size,
)


def test_grid_size_matches_address_space():
    grid = generate_grid()
    assert len(grid) == grid_size()
    expected = sum(len(BLOCKS_BY_PHASE[p]) for p in PHASES) * HOUSES_PER_BLOCK
    assert grid_size() == expected


def test_every_phase_has_blocks():
    assert set(BLOCKS_BY_PHASE) == set(PHASES)
    assert all(BLOCKS_BY_PHASE[p] for p in PHASES)


def test_sectors_is_the_deduplicated_union_of_all_blocks():
    union = {b for blocks in BLOCKS_BY_PHASE.values() for b in blocks}
    assert set(SECTORS) == union
    assert len(SECTORS) == len(set(SECTORS)), "no duplicates"


def test_real_phase_8_blocks_are_present():
    # These are the names residents actually use; an owner must be able to find them.
    p8 = set(BLOCKS_BY_PHASE[8])
    for name in ("Umer Block", "Ali Block", "Abu Bakar Block", "Overseas Enclave",
                 "Awami Villas 2", "Sector E-1", "Sector P"):
        assert name in p8, name


def test_plot_refs_are_unique():
    grid = generate_grid()
    keys = {(p.phase, p.sector, p.house_ref) for p in grid}
    assert len(keys) == len(grid), "phase/sector/house_ref must be unique (DB unique constraint)"

    possession = {p.possession_ref for p in grid}
    assert len(possession) == len(grid), "possession_ref must be unique"


def test_house_ref_is_a_bare_number_starting_at_one_per_block():
    # Real house numbers restart at 1 in every block; they are not a phase-derived formula
    # and carry no sector suffix (an owner types "129", not "929-C").
    grid = generate_grid()
    for p in grid:
        assert p.house_ref.isdigit(), p.house_ref
        assert 1 <= int(p.house_ref) <= HOUSES_PER_BLOCK

    for phase, blocks in BLOCKS_BY_PHASE.items():
        for block in blocks:
            nums = sorted(int(p.house_ref) for p in grid
                          if p.phase == f"Phase {phase}" and p.sector == block)
            assert nums == list(range(1, HOUSES_PER_BLOCK + 1))


def test_street_groups_houses_and_is_consistent():
    for p in generate_grid():
        m = re.fullmatch(r"Street (\d+)", p.street)
        assert m, p.street
        expected = (int(p.house_ref) - 1) // HOUSES_PER_STREET + 1
        assert int(m.group(1)) == expected


def test_address_reads_the_way_a_resident_writes_it():
    p = next(x for x in generate_grid() if x.sector == "Umer Block")
    assert p.address == f"House {p.house_ref}, {p.street}, Umer Block, {p.phase}"


def test_sizes_are_real_bahria_categories():
    valid = set(HOUSE_SIZES)
    # The CLAUDE.md s.0 trio must remain valid; 7/8-marla and 2-kanal are also genuinely sold.
    assert {"5-marla", "10-marla", "1-kanal"} <= valid
    assert all(p.size in valid for p in generate_grid())


SAFARI_VALLEY = {"Abu Bakar Block", "Umer Block", "Usman Block", "Ali Block",
                 "Rafi Block", "Khalid Block", "Awais Block"}


def test_safari_valley_is_five_or_seven_marla():
    # Safari Valley is a documented 5/7-marla zone.
    plots = [p for p in generate_grid() if p.sector in SAFARI_VALLEY]
    assert plots, "Safari Valley blocks must exist in the grid"
    assert {p.size for p in plots} == {"5-marla", "7-marla"}


def test_generation_is_deterministic():
    # Idempotent seed depends on byte-identical re-generation.
    assert generate_grid() == generate_grid()


def test_coordinates_near_bahria():
    for p in generate_grid():
        assert 33.4 <= p.lat <= 33.9
        assert 72.9 <= p.lng <= 73.4


def test_wkt_is_lng_lat_order():
    p = generate_grid()[0]
    assert p.wkt.startswith("POINT(")
    lng_s, lat_s = p.wkt[len("POINT(") : -1].split(" ")
    assert float(lng_s) == round(p.lng, 6)
    assert float(lat_s) == round(p.lat, 6)
