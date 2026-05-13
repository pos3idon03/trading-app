"""Tests for buy-and-hold curve generation in the backtesting runner."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.runner import _compute_buy_hold_curve, run_backtest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def flat_close():
    """Close series that stays constant at 100."""
    dates = pd.date_range("2022-01-01", periods=10, freq="D")
    return pd.Series([100.0] * 10, index=dates)


@pytest.fixture
def rising_close():
    """Close series that doubles over 10 bars."""
    dates = pd.date_range("2022-01-01", periods=10, freq="D")
    prices = np.linspace(100.0, 200.0, 10)
    return pd.Series(prices, index=dates)


@pytest.fixture
def ohlcv_df():
    """Minimal OHLCV DataFrame with 100 bars for integration test."""
    rng = np.random.default_rng(0)
    n = 100
    returns = rng.normal(0.001, 0.01, n)
    close = pd.Series(50.0 * np.cumprod(1 + returns))
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
# Unit tests for _compute_buy_hold_curve
# ---------------------------------------------------------------------------

class TestComputeBuyHoldCurve:
    def test_starts_at_initial_capital(self, rising_close):
        curve = _compute_buy_hold_curve(rising_close, initial_capital=100_000.0)
        assert curve[0]["value"] == pytest.approx(100_000.0)

    def test_length_matches_close_series(self, rising_close):
        curve = _compute_buy_hold_curve(rising_close, initial_capital=100_000.0)
        assert len(curve) == len(rising_close)

    def test_doubles_when_price_doubles(self, rising_close):
        curve = _compute_buy_hold_curve(rising_close, initial_capital=100_000.0)
        assert curve[-1]["value"] == pytest.approx(200_000.0, rel=1e-3)

    def test_flat_price_stays_constant(self, flat_close):
        curve = _compute_buy_hold_curve(flat_close, initial_capital=100_000.0)
        for point in curve:
            assert point["value"] == pytest.approx(100_000.0)

    def test_returns_empty_list_for_zero_first_price(self):
        dates = pd.date_range("2022-01-01", periods=3, freq="D")
        zero_close = pd.Series([0.0, 100.0, 200.0], index=dates)
        curve = _compute_buy_hold_curve(zero_close, initial_capital=100_000.0)
        assert curve == []

    def test_each_point_has_time_and_value_keys(self, rising_close):
        curve = _compute_buy_hold_curve(rising_close, initial_capital=50_000.0)
        for point in curve:
            assert "time" in point
            assert "value" in point


# ---------------------------------------------------------------------------
# Integration test: run_backtest returns buy_hold_curve
# ---------------------------------------------------------------------------

class TestRunBacktestBuyHoldIntegration:
    def test_buy_hold_curve_present(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="ma_crossover", params={})
        assert result.buy_hold_curve is not None
        assert len(result.buy_hold_curve) > 0

    def test_buy_hold_curve_starts_at_initial_capital(self, ohlcv_df):
        capital = 100_000.0
        result = run_backtest(ohlcv_df, strategy="ma_crossover", params={}, initial_capital=capital)
        assert result.buy_hold_curve[0]["value"] == pytest.approx(capital, rel=1e-4)

    def test_buy_hold_curve_same_length_as_equity_curve(self, ohlcv_df):
        result = run_backtest(ohlcv_df, strategy="ma_crossover", params={})
        assert len(result.buy_hold_curve) == len(result.equity_curve)
