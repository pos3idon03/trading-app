from features.fred.release_date_fallback import (
    SAME_DAY_RELEASE_SERIES,
    uses_same_day_release_fallback,
)


def test_same_day_release_series_includes_daily_rates():
    assert SAME_DAY_RELEASE_SERIES == frozenset({"DFF", "DGS2", "DGS10", "T10Y2Y"})


def test_uses_same_day_release_fallback():
    assert uses_same_day_release_fallback("DFF")
    assert uses_same_day_release_fallback("T10Y2Y")
    assert not uses_same_day_release_fallback("CPIAUCSL")
    assert not uses_same_day_release_fallback("DCOILWTICO")
