"""Tests for the indicator calculation engine."""
import numpy as np
import pandas as pd
import pytest

from features.live_trading.indicator_engine import (
    MIN_BARS_REQUIRED,
    IndicatorSnapshot,
    _build_dataframe,
    calculate_rsi,
    calculate_vwap,
    compute_indicators,
)
from features.live_trading.resampler import OHLCVBar
from datetime import datetime, timezone, timedelta


def _make_bars(n: int, base_price: float = 100.0) -> list[OHLCVBar]:
    """Generate synthetic OHLCVBar objects."""
    rng = np.random.default_rng(42)
    prices = base_price + np.cumsum(rng.normal(0, 0.5, n))
    bars = []
    for i in range(n):
        p = prices[i]
        bars.append(OHLCVBar(
            symbol="TEST",
            timeframe="1h",
            open=p - 0.5,
            high=p + 1.0,
            low=p - 1.0,
            close=p,
            volume=int(rng.integers(100_000, 1_000_000)),
            vwap=p,
            bar_start=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i),
            bar_end=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i + 1),
            tick_count=100,
        ))
    return bars


class TestBuildDataframe:
    def test_columns_lowercase(self):
        bars = _make_bars(5)
        df = _build_dataframe(bars)
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]

    def test_row_count(self):
        bars = _make_bars(50)
        df = _build_dataframe(bars)
        assert len(df) == 50


class TestCalculateRSI:
    def test_returns_series(self):
        close = pd.Series(np.random.default_rng(42).normal(100, 2, 50))
        result = calculate_rsi(close, length=14)
        assert isinstance(result, pd.Series)
        assert len(result) == 50

    def test_values_in_range(self):
        close = pd.Series(np.random.default_rng(42).normal(100, 2, 100))
        result = calculate_rsi(close, length=14)
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()


class TestCalculateVWAP:
    def test_basic_vwap(self):
        high = pd.Series([105.0, 110.0, 108.0])
        low = pd.Series([95.0, 100.0, 102.0])
        close = pd.Series([100.0, 105.0, 105.0])
        volume = pd.Series([1000, 2000, 1500])
        result = calculate_vwap(high, low, close, volume)
        assert len(result) == 3
        assert result.iloc[-1] > 0


class TestComputeIndicators:
    def test_returns_none_for_insufficient_bars(self):
        bars = _make_bars(10)
        result = compute_indicators(bars, "TEST", "1h")
        assert result is None

    def test_returns_snapshot_for_sufficient_bars(self):
        bars = _make_bars(100)
        result = compute_indicators(bars, "TEST", "1h")
        assert result is not None
        assert isinstance(result, IndicatorSnapshot)
        assert result.symbol == "TEST"
        assert result.timeframe == "1h"
        assert result.close_price > 0

    def test_rsi_populated(self):
        bars = _make_bars(100)
        result = compute_indicators(bars, "TEST", "1h")
        assert result.rsi is not None
        assert 0 <= result.rsi <= 100

    def test_macd_populated(self):
        bars = _make_bars(100)
        result = compute_indicators(bars, "TEST", "1h")
        assert result.macd is not None
        assert result.macd_signal is not None
        assert result.macd_histogram is not None

    def test_bollinger_populated(self):
        bars = _make_bars(100)
        result = compute_indicators(bars, "TEST", "1h")
        assert result.bb_upper is not None
        assert result.bb_middle is not None
        assert result.bb_lower is not None
        assert result.bb_upper > result.bb_lower

    def test_vwap_populated(self):
        bars = _make_bars(100)
        result = compute_indicators(bars, "TEST", "1h")
        assert result.vwap is not None
        assert result.vwap > 0

    def test_to_dict(self):
        bars = _make_bars(100)
        result = compute_indicators(bars, "TEST", "1h")
        d = result.to_dict()
        assert "rsi" in d
        assert "macd" in d
        assert "bb_upper" in d
        assert "vwap" in d
