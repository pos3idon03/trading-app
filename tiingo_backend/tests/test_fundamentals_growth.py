from features.market_data.fundamentals_growth import compute_metric_growth


def _row(period: str, value: float) -> dict:
    return {"period": period, "value": value}


def test_yoy_and_qoq_for_latest_quarter():
    rows = [
        _row("2024-Q3", 110.0),
        _row("2024-Q2", 105.0),
        _row("2024-Q1", 100.0),
        _row("2023-Q4", 95.0),
        _row("2023-Q3", 100.0),
        _row("2023-Q2", 90.0),
        _row("2023-Q1", 80.0),
    ]
    growth = compute_metric_growth(rows)

    assert growth.latest_period == "2024-Q3"
    assert growth.yoy == 10.0
    assert growth.qoq == round((110 - 105) / 105 * 100, 2)


def test_cagr_annualized_over_four_quarters():
    rows = [
        _row("2024-Q3", 110.0),
        _row("2024-Q2", 105.0),
        _row("2024-Q1", 100.0),
        _row("2023-Q4", 95.0),
    ]
    growth = compute_metric_growth(rows)

    expected = round(((110 / 95) ** (4 / 3) - 1) * 100, 2)
    assert growth.cagr == expected


def test_cagr_none_with_fewer_than_four_quarters():
    rows = [_row("2024-Q1", 100.0), _row("2023-Q4", 90.0)]
    growth = compute_metric_growth(rows)

    assert growth.cagr is None


def test_qoq_wraps_q1_to_prior_year_q4():
    rows = [
        _row("2024-Q1", 120.0),
        _row("2023-Q4", 100.0),
    ]
    growth = compute_metric_growth(rows)

    assert growth.latest_period == "2024-Q1"
    assert growth.qoq == 20.0
    assert growth.yoy is None


def test_missing_prior_quarter_returns_none():
    rows = [_row("2024-Q2", 50.0)]
    growth = compute_metric_growth(rows)

    assert growth.yoy is None
    assert growth.qoq is None
    assert growth.cagr is None


def test_zero_prior_value_returns_none():
    rows = [
        _row("2024-Q1", 100.0),
        _row("2023-Q1", 0.0),
    ]
    growth = compute_metric_growth(rows)

    assert growth.yoy is None


def test_empty_rows():
    growth = compute_metric_growth([])

    assert growth.latest_period is None
    assert growth.yoy is None
    assert growth.qoq is None
    assert growth.cagr is None
