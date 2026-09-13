"""Apify item normalizer — pure, runs anywhere with just pytest."""
import pytest

from app.integrations.normalize import normalize_item, parse_area, parse_rent, parse_size


@pytest.mark.parametrize(
    "value,expected",
    [
        (150000, 150000),
        ("Rs 150,000", 150000),
        ("1.5 Lakh", 150000),
        ("2 Crore", 20000000),
        ("", None),
        (None, None),
    ],
)
def test_parse_rent(value, expected):
    assert parse_rent(value) == expected


def test_parse_size():
    assert parse_size("10 Marla") == "10-marla"
    assert parse_size("1 Kanal") == "1-kanal"
    assert parse_size("7.6 Marla") == "7.6-marla"
    assert parse_size("no area given") == "5-marla"


def test_parse_area_fits_columns():
    phase, sector = parse_area("Bahria Town Phase 8 - Block H, Rawalpindi")
    assert phase == "Phase 8"
    assert sector == "H"
    assert len(phase) <= 16 and len(sector) <= 64
    assert parse_area("Chaklala Scheme 3")[0] == "Chaklala 3"
    assert parse_area("DHA Defence, Rawalpindi")[0][:3] == "DHA"


def test_normalize_full_item():
    item = {
        "url": "https://example.com/listing/123",
        "price": "Rs 185,000",
        "location": "Bahria Town Phase 4, Rawalpindi",
        "area": "10 Marla",
        "bedrooms": 4,
        "bathrooms": 4,
    }
    out = normalize_item(item)
    assert out["external_ref"] == "apify:https://example.com/listing/123"
    assert out["phase"] == "Phase 4"
    assert out["size"] == "10-marla"
    assert out["rent"] == 185000
    assert out["beds"] == 4 and out["baths"] == 4
    assert out["house_ref"].startswith("IMP-")


def test_normalize_skips_incomplete():
    assert normalize_item({"location": "Somewhere"}) is None       # no rent
    assert normalize_item({"price": "Rs 50,000"}) is None          # no location
    assert normalize_item({"price": "Rs 50,000", "location": "X"}) is None  # no url/id


def test_normalize_defaults_beds_when_missing():
    out = normalize_item({"id": "abc", "price": 90000, "location": "Bahria Phase 2", "area": "5 Marla"})
    assert out["beds"] >= 1 and out["baths"] >= 1


def test_normalize_real_zameen_actor_shape():
    # Shape from shahidirfan/Zameen-com-Scraper: numeric price, sqft area, size in title, photos.
    item = {
        "title": "2.5 Kanal Designer House For Rent in Bahria Phase 8",
        "price": 1000000,
        "area": 11250,
        "area_unit": "sqft",
        "bedrooms": 8,
        "bathrooms": 6,
        "location": "Bahria Town Rawalpindi, Bahria Town Phase 8, Overseas Enclave",
        "photos": ["https://media.zameen.com/a.webp", "https://media.zameen.com/b.webp"],
        "url": "https://www.zameen.com/Property/x-123.html",
        "phone_number": "+923001234567",  # must NOT be carried into the listing
    }
    out = normalize_item(item)
    assert out["size"] == "2.5-kanal"          # parsed from the title
    assert out["phase"] == "Phase 8"
    assert out["rent"] == 1000000
    assert out["beds"] == 8 and out["baths"] == 6
    assert out["photos"] == ["https://media.zameen.com/a.webp", "https://media.zameen.com/b.webp"]
    assert "phone_number" not in out  # agent contact dropped (rule 7)


def test_size_from_sqft_when_no_title_size():
    out = normalize_item({"url": "u", "price": 90000, "location": "Phase 4", "area": 1125, "area_unit": "sqft"})
    assert out["size"] == "5-marla"  # 1125 sqft / 225 = 5 marla


def test_named_sub_scheme_is_kept_whole_not_truncated():
    # "Overseas Enclave" is the address residents give; the old 8-char column clipped it.
    phase, sector = parse_area("Bahria Town Rawalpindi, Bahria Town Phase 8, Overseas Enclave")
    assert phase == "Phase 8"
    assert sector == "Overseas Enclave"


def test_named_sub_scheme_wins_over_a_bare_block_letter():
    _, sector = parse_area("Bahria Town Phase 8, Safari Valley, Block B")
    assert sector == "Safari Valley"


def test_falls_back_to_block_letter_then_main():
    assert parse_area("Bahria Town Phase 8 - Block H, Rawalpindi")[1] == "H"
    assert parse_area("Bahria Town Phase 5")[1] == "Main"
