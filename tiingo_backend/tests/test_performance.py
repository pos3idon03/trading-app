from datetime import date, datetime, timezone

from features.market_data.performance import compute_performance, compute_performance_breakdown


def _bar(time_str: str, close: float, div_cash: float = 0) -> dict:
    return {
        "time": datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc),
        "close": close,
        "div_cash": div_cash,
    }


def test_compute_performance_1w():
    bars = [
        _bar("2024-01-01T00:00:00", 100.0),
        _bar("2024-01-08T00:00:00", 110.0),
    ]
    result = compute_performance(bars)
    assert result["1W"] == 10.0


def test_compute_performance_missing_history():
    bars = [_bar("2024-06-01T00:00:00", 50.0)]
    result = compute_performance(bars)
    assert result["1W"] is None
    assert result["1M"] is None


def test_compute_performance_ytd():
    bars = [
        _bar("2023-12-29T00:00:00", 100.0),
        _bar("2024-06-15T00:00:00", 120.0),
    ]
    result = compute_performance(bars)
    assert result["YTD"] == 20.0


def test_breakdown_price_only():
    bars = [
        _bar("2024-01-01T00:00:00", 100.0),
        _bar("2024-01-08T00:00:00", 110.0),
    ]
    row = next(r for r in compute_performance_breakdown(bars) if r["period"] == "1W")
    assert row["price_change_pct"] == 10.0
    assert row["dividend_return_pct"] == 0.0
    assert row["total_return_pct"] == 10.0
    assert row["example_outcome"] == 110.0
    assert row["example_dividend_income"] == 0.0


def test_breakdown_includes_dividends():
    bars = [
        _bar("2024-01-01T00:00:00", 100.0),
        _bar("2024-01-05T00:00:00", 102.0, div_cash=1.0),
        _bar("2024-01-08T00:00:00", 110.0),
    ]
    row = next(r for r in compute_performance_breakdown(bars) if r["period"] == "1W")
    assert row["price_change_pct"] == 10.0
    assert row["dividend_return_pct"] == 1.0
    assert row["total_return_pct"] == 11.0
    assert row["example_dividend_income"] == 1.0
    assert row["example_outcome"] == 111.0


def test_reference_date_ytd():
    from features.market_data.performance import _reference_date

    as_of = date(2024, 6, 15)
    assert _reference_date(as_of, "YTD") == date(2024, 1, 1)


def test_compute_performance_2y_and_5y():
    bars = [
        _bar("2019-01-02T00:00:00", 100.0),
        _bar("2024-06-01T00:00:00", 150.0),
    ]
    result = compute_performance(bars)
    assert result["2Y"] == 50.0
    assert result["5Y"] == 50.0
