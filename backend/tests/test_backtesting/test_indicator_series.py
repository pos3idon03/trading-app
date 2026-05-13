"""Tests for indicator_series generation in the backtesting runner."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.runner import _compute_indicator_series, run_backtest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ohlcv_df():
    """Minimal OHLCV DataFrame with 120 bars for integration tests."""
    rng = np.random.default_rng(42)
    n = 120
    returns = rng.normal(0.001, 0.01, n)
    close = pd.Series(100.0 * np.cumprod(1 + returns))
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "time": dates,
        "open": close.values,
        "high": close.values * 1.005,
        "low": close.values * 0.995,
        "close": close.values,
        "volume": 1_000.0,
    })


# ---------------------------------------------------------------------------
# Unit tests for _compute_indicator_series
# ---------------------------------------------------------------------------

class TestComputeIndicatorSeries:
    def test_ema_cross_returns_fast_slow_keys(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "ema_cross", {})
        assert len(series) > 0
        assert "fast_ema" in series[0]
        assert "slow_ema" in series[0]

    def test_rsi_returns_rsi_key(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "rsi", {})
        assert len(series) > 0
        assert "rsi" in series[0]

    def test_macd_returns_macd_and_signal_keys(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "macd", {})
        assert len(series) > 0
        assert "macd" in series[0]
        assert "signal" in series[0]

    def test_aroon_returns_aroon_up_and_down(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "aroon", {})
        assert len(series) > 0
        assert "aroon_up" in series[0]
        assert "aroon_down" in series[0]

    def test_gap_fade_returns_empty(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "gap_fade", {})
        assert series == []

    def test_seasonal_returns_empty(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "seasonal", {})
        assert series == []

    def test_orb_returns_empty(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "orb", {})
        assert series == []

    def test_every_row_has_time_key(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "ema_cross", {})
        for row in series:
            assert "time" in row

    def test_nan_values_converted_to_none(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "ema_cross", {})
        indicator_values = [
            v
            for row in series
            for k, v in row.items()
            if k != "time"
        ]
        for v in indicator_values:
            assert v is None or isinstance(v, float)

    def test_length_matches_input_dataframe(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "rsi", {})
        assert len(series) == len(ohlcv_df)

    def test_unknown_strategy_returns_empty(self, ohlcv_df):
        series = _compute_indicator_series(ohlcv_df, "nonexistent_strategy", {})
        assert series == []


# ---------------------------------------------------------------------------
# Integration tests: run_backtest includes indicator_series
# ---------------------------------------------------------------------------

class TestRunBacktestIndicatorIntegration:
    def test_indicator_series_present_for_ema_cross(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="ema_cross", params={})
        assert result.indicator_series is not None
        assert len(result.indicator_series) > 0

    def test_indicator_series_length_matches_equity_curve(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="ema_cross", params={})
        assert len(result.indicator_series) == len(result.equity_curve)

    def test_indicator_series_empty_for_gap_fade(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="gap_fade", params={})
        assert result.indicator_series == []

    def test_indicator_series_has_correct_keys_for_macd(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="macd", params={})
        assert len(result.indicator_series) > 0
        first = result.indicator_series[0]
        assert "macd" in first
        assert "signal" in first
        assert "time" in first

    def test_indicator_series_rsi_values_in_range(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="rsi", params={})
        for row in result.indicator_series:
            v = row.get("rsi")
            if v is not None:
                assert 0.0 <= v <= 100.0

    @pytest.mark.parametrize("strategy", [
        "ma_crossover", "sma_cross", "ema_cross", "sma_break",
        "macd", "rsi", "lrsi", "aroon", "stoch_rsi",
        "mean_reversion", "breakout", "range_breakout",
    ])
    def test_indicator_series_non_empty_for_strategy(self, ohlcv_df, strategy):
        result = run_backtest(ohlcv_df, strategy=strategy, params={})
        assert result.indicator_series is not None
        assert len(result.indicator_series) > 0
