"""Fallback release_date logic for FRED series that reject ALFRED vintages."""

# Daily Treasury / Fed rate series return 400 from FRED when output_type=1.
# Same-day publication is correct for point-in-time ML joins on these series.
SAME_DAY_RELEASE_SERIES = frozenset({"DFF", "DGS2", "DGS10", "T10Y2Y"})


def uses_same_day_release_fallback(series_id: str) -> bool:
    return series_id in SAME_DAY_RELEASE_SERIES
