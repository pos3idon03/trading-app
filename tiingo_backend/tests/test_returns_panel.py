from datetime import date, datetime, timezone

from features.backtesting.returns_panel import align_bars_by_date


def _bar(d: date, close: float) -> dict:
    return {
        "time": datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
    }


def test_align_bars_intersection():
    bars_a = [_bar(date(2024, 1, 1), 100), _bar(date(2024, 1, 2), 101)]
    bars_b = [_bar(date(2024, 1, 2), 50), _bar(date(2024, 1, 3), 51)]
    dates, aligned = align_bars_by_date({"A": bars_a, "B": bars_b})
    assert dates == [date(2024, 1, 2)]
    assert len(aligned["A"]) == 1
    assert len(aligned["B"]) == 1
