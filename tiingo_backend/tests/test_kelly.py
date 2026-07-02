from features.portfolio.kelly import capped_kelly_budget, kelly_fraction


def test_kelly_fraction_positive_edge():
    f = kelly_fraction(0.6, 100.0, 50.0)
    assert f > 0


def test_capped_kelly_respects_cap():
    budget = capped_kelly_budget(
        10_000,
        0.6,
        100.0,
        50.0,
        kelly_cap=0.25,
        max_position_pct=10.0,
    )
    assert budget <= 1_000
