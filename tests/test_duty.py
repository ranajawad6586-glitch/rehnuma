"""Stamp-duty bands + advisories + HTML rendering — pure, runs with just pytest."""
from app.agreements.advisories import build_advisories
from app.agreements.duty import compute_stamp_duty, stamp_duty_for_monthly_rent
from app.agreements.render import build_agreement_html, build_police_verification_html


def test_duty_bands():
    assert compute_stamp_duty(100_000).duty == 500       # boundary -> low band
    assert compute_stamp_duty(100_001).duty == 1_000
    assert compute_stamp_duty(500_000).duty == 1_000     # boundary -> mid band
    assert compute_stamp_duty(500_001).duty == 2_000
    assert compute_stamp_duty(2_400_000).duty == 2_000


def test_duty_from_monthly_rent_uses_annual():
    d = stamp_duty_for_monthly_rent(50_000)  # 600,000/yr
    assert d.annual_rent == 600_000
    assert d.duty == 2_000


def test_advisories_are_hedged_and_never_fix_rs_200():
    adv = build_advisories(12)
    blob = " ".join(adv).lower()
    assert "not universally correct" in blob
    assert "police" in blob and "maintenance dues" in blob
    # e-stamping advisory only for 12m+ terms.
    assert any("e-stamping" in a for a in adv)
    assert not any("e-stamping" in a for a in build_advisories(3))


def test_agreement_html_contains_terms_and_duty():
    ctx = {
        "date": "2026-06-01", "owner_name": "Owner A", "tenant_name": "Tenant B",
        "size": "10-marla", "sector": "Sector C, Phase 4", "house_ref": "500-C",
        "rent": 175000, "advance_months": 3, "security": 175000, "duration_months": 12,
        "move_in": "2026-08-01", "notice_weeks": 4, "annual_rent": 2_100_000,
        "stamp_duty_label": "Rs 2,000 (annual rent over Rs 500,000)",
        "advisories": build_advisories(12),
    }
    html = build_agreement_html(ctx)
    assert "TENANCY AGREEMENT" in html
    assert "Rs 175,000" in html
    assert "Rs 2,000" in html
    assert "500-C" in html
    assert "4 weeks" in html


def test_police_form_leaves_cnic_blank():
    ctx = {
        "date": "2026-06-01", "owner_name": "Owner A", "tenant_name": "Tenant B",
        "size": "10-marla", "sector": "Sector C, Phase 4", "house_ref": "500-C",
        "duration_months": 12, "move_in": "2026-08-01",
    }
    html = build_police_verification_html(ctx)
    assert "TENANT VERIFICATION FORM" in html
    assert "blank" in html  # blank fields rendered (CNIC etc. filled by hand)
    assert "Tenant B" in html
