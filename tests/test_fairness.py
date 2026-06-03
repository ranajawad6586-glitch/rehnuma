"""Offer "Fair?" evaluator — pure, runs anywhere with just pytest."""
from app.deals.fairness import evaluate_fairness


def test_within_norms_is_fair():
    f = evaluate_fairness(asking_rent=180000, rent=180000, advance_months=3, security=180000)
    assert f.is_fair is True
    assert f.flags == []
    assert "fair" in f.verdict.lower()


def test_six_months_advance_is_red_flag():
    f = evaluate_fairness(asking_rent=180000, rent=180000, advance_months=6, security=180000)
    assert f.is_fair is False
    assert any("red flag" in flag for flag in f.flags)


def test_advance_above_norm_but_not_red_flag():
    f = evaluate_fairness(asking_rent=180000, rent=180000, advance_months=4, security=180000)
    assert f.is_fair is True  # noted, not a hard red flag
    assert any("above the usual" in flag for flag in f.flags)


def test_rent_below_asking_is_noted_favourably():
    f = evaluate_fairness(asking_rent=200000, rent=180000, advance_months=3, security=180000)
    assert f.is_fair is True
    assert "below asking" in f.verdict


def test_security_exceeding_one_month_flagged():
    f = evaluate_fairness(asking_rent=180000, rent=180000, advance_months=3, security=400000)
    assert any("exceeds one month" in flag for flag in f.flags)


def test_zero_security_flagged():
    f = evaluate_fairness(asking_rent=180000, rent=180000, advance_months=3, security=0)
    assert any("no security" in flag for flag in f.flags)
