"""Unit tests for the Bahria grid generator.

Pure stdlib — no DB, no FastAPI, no third-party imports — so these run on any Python 3.9+
with just pytest installed. They are the runnable verification for M1's seed logic.
"""
from app.grid.bahria import (
    HOUSES_PER_SECTOR,
    HOUSE_SIZES,
    PHASES,
    SECTORS,
    generate_grid,
    grid_size,
)


def test_grid_size_matches_address_space():
    grid = generate_grid()
    assert len(grid) == grid_size()
    assert grid_size() == len(PHASES) * len(SECTORS) * HOUSES_PER_SECTOR


def test_plot_refs_are_unique():
    grid = generate_grid()
    keys = {(p.phase, p.sector, p.house_ref) for p in grid}
    assert len(keys) == len(grid), "phase/sector/house_ref must be unique (DB unique constraint)"

    possession = {p.possession_ref for p in grid}
    assert len(possession) == len(grid), "possession_ref must be unique"


def test_house_ref_format():
    # CLAUDE.md s.3: house reference format e.g. "287-C" within Sector C.
    for p in generate_grid():
        num, _, suffix = p.house_ref.partition("-")
        assert num.isdigit()
        assert suffix == p.sector


def test_sizes_are_standard_categories():
    valid = set(HOUSE_SIZES)
    assert valid == {"5-marla", "10-marla", "1-kanal"}
    assert all(p.size in valid for p in generate_grid())


def test_generation_is_deterministic():
    # Idempotent seed depends on byte-identical re-generation.
    a = generate_grid()
    b = generate_grid()
    assert a == b


def test_coordinates_near_bahria_isb():
    for p in generate_grid():
        assert 33.4 <= p.lat <= 33.8
        assert 73.0 <= p.lng <= 73.4


def test_wkt_is_lng_lat_order():
    p = generate_grid()[0]
    assert p.wkt.startswith("POINT(")
    inner = p.wkt[len("POINT(") : -1]
    lng_s, lat_s = inner.split(" ")
    assert float(lng_s) == round(p.lng, 6)
    assert float(lat_s) == round(p.lat, 6)
