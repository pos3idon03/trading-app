"""Shared timeframe constants and helpers."""
from __future__ import annotations

SIGNAL_TIMEFRAMES: frozenset[str] = frozenset(
    {"5m", "15m", "30m", "1h", "4h", "1d", "1w"}
)

# Legacy live-trading value; normalized on read/write where applicable.
LEGACY_TIMEFRAMES: frozenset[str] = frozenset({"1m", "3h"})

TIMEFRAME_DURATION_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "3h": 10_800_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
}


def normalize_timeframe(tf: str) -> str:
    """Map legacy timeframes to the canonical signal set."""
    if tf == "3h":
        return "4h"
    if tf == "1m":
        return "5m"
    return tf


def validate_signal_timeframe(tf: str) -> str:
    """Return normalized timeframe or raise ValueError."""
    normalized = normalize_timeframe(tf)
    if normalized not in SIGNAL_TIMEFRAMES:
        raise ValueError(
            f"Invalid timeframe {tf!r}. Allowed: {sorted(SIGNAL_TIMEFRAMES)}"
        )
    return normalized


def timeframe_duration_ms(tf: str) -> int:
    return TIMEFRAME_DURATION_MS.get(normalize_timeframe(tf), TIMEFRAME_DURATION_MS["1d"])


def finest_timeframe(timeframes: list[str]) -> str:
    """Return the shortest-duration timeframe from a list (defaults to 1d)."""
    if not timeframes:
        return "1d"
    return min(timeframes, key=timeframe_duration_ms)
