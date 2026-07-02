from datetime import date, datetime, timezone

from features.backtesting.survivorship import build_survivorship_warnings


def test_survivorship_warning_when_bars_end_early():
    bars = [{
        "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "close": 100,
    }]
    warnings = build_survivorship_warnings(
        symbols=["XYZ"],
        instruments={"XYZ": {"delist_reason": "bankrupt"}},
        bars_by_symbol={"XYZ": bars},
        requested_end=date(2024, 6, 1),
    )
    assert any("before requested end" in w for w in warnings)
