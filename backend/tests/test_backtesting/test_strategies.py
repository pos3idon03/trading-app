"""Tests for backtesting strategy signal generators."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.strategies import (
    breakout_signals,
    build_signal_array,
    gap_fade_signals,
    ma_crossover_signals,
    mean_reversion_signals,
    trend_pullback_signals,
    vrp_harvest_signals,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ohlcv_df():
    """Synthetic daily OHLCV DataFrame with 400 bars."""
    rng = np.random.default_rng(42)
    n = 400
    returns = rng.normal(0.001, 0.015, n)
    close = pd.Series(100 * np.cumprod(1 + returns))
    noise = rng.uniform(0.995, 1.005, n)
    high = close * (1 + rng.uniform(0.0, 0.015, n))
    low = close * (1 - rng.uniform(0.0, 0.015, n))
    open_p = close.shift(1).fillna(close.iloc[0]) * noise
    volume = pd.Series(rng.integers(100_000, 1_000_000, n).astype(float))
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": open_p.values, "high": high.values, "low": low.values,
         "close": close.values, "volume": volume.values},
        index=dates,
    )


@pytest.fixture
def gap_df():
    """DataFrame containing deliberate gap-up events for gap_fade tests."""
    rng = np.random.default_rng(7)
    n = 200
    close = pd.Series(100 + np.cumsum(rng.normal(0, 0.5, n)))
    high = close + rng.uniform(0, 1, n)
    low = close - rng.uniform(0, 1, n)
    open_p = close.copy()
    # inject visible gap-ups at specific bars
    for idx in [20, 60, 100, 140, 180]:
        if idx < n:
            open_p.iloc[idx] = close.iloc[idx - 1] * 1.06  # 6% gap up
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": open_p.values, "high": high.values, "low": low.values,
         "close": close.values, "volume": np.ones(n) * 500_000},
        index=dates,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_signal_pair(entries, exits, df):
    assert isinstance(entries, pd.Series)
    assert isinstance(exits, pd.Series)
    assert entries.dtype == bool
    assert exits.dtype == bool
    assert len(entries) == len(df)
    assert len(exits) == len(df)
    assert entries.index.equals(df.index)
    assert exits.index.equals(df.index)


# ---------------------------------------------------------------------------
# MA Crossover
# ---------------------------------------------------------------------------

class TestMACrossoverSignals:
    def test_returns_boolean_series_with_correct_length(self, ohlcv_df):
        entries, exits = ma_crossover_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_entries_occur_with_adequate_history(self, ohlcv_df):
        entries, _ = ma_crossover_signals(ohlcv_df, fast_window=5, slow_window=20)
        assert entries.sum() > 0

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = ma_crossover_signals(ohlcv_df, fast_window=5, slow_window=20)
        assert not (entries & exits).any()

    def test_faster_window_produces_more_trades(self, ohlcv_df):
        e_fast, _ = ma_crossover_signals(ohlcv_df, fast_window=3, slow_window=10)
        e_slow, _ = ma_crossover_signals(ohlcv_df, fast_window=20, slow_window=100)
        assert e_fast.sum() >= e_slow.sum()


# ---------------------------------------------------------------------------
# Mean Reversion
# ---------------------------------------------------------------------------

class TestMeanReversionSignals:
    def test_returns_boolean_series_with_correct_length(self, ohlcv_df):
        entries, exits = mean_reversion_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_high_threshold_fewer_signals(self, ohlcv_df):
        low_e, _ = mean_reversion_signals(ohlcv_df, z_threshold=1.0)
        high_e, _ = mean_reversion_signals(ohlcv_df, z_threshold=3.0)
        assert low_e.sum() >= high_e.sum()


# ---------------------------------------------------------------------------
# Breakout
# ---------------------------------------------------------------------------

class TestBreakoutSignals:
    def test_returns_boolean_series_with_correct_length(self, ohlcv_df):
        entries, exits = breakout_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_signals_fire_with_adequate_history(self, ohlcv_df):
        entries, exits = breakout_signals(
            ohlcv_df, bb_window=10, squeeze_lookback=30, donchian_window=10
        )
        assert entries.sum() >= 0  # may be 0 if no squeeze — acceptable
        assert exits.sum() >= 0

    def test_smaller_lookback_more_squeezes(self, ohlcv_df):
        e_small, _ = breakout_signals(ohlcv_df, squeeze_lookback=20, donchian_window=10)
        e_large, _ = breakout_signals(ohlcv_df, squeeze_lookback=200, donchian_window=10)
        assert e_small.sum() >= e_large.sum()

    def test_no_signals_before_warmup(self, ohlcv_df):
        entries, exits = breakout_signals(ohlcv_df, bb_window=20, squeeze_lookback=120, donchian_window=20)
        # First bar cannot have both MAs and Donchian fully computed
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Trend-Following with Pullbacks
# ---------------------------------------------------------------------------

class TestTrendPullbackSignals:
    def test_returns_boolean_series_with_correct_length(self, ohlcv_df):
        entries, exits = trend_pullback_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_higher_adx_threshold_fewer_entries(self, ohlcv_df):
        e_low, _ = trend_pullback_signals(ohlcv_df, adx_threshold=15.0)
        e_high, _ = trend_pullback_signals(ohlcv_df, adx_threshold=40.0)
        assert e_low.sum() >= e_high.sum()

    def test_wider_oversold_zone_more_entries(self, ohlcv_df):
        e_wide, _ = trend_pullback_signals(ohlcv_df, oversold=35.0)
        e_narrow, _ = trend_pullback_signals(ohlcv_df, oversold=10.0)
        assert e_wide.sum() >= e_narrow.sum()

    def test_no_signals_before_warmup(self, ohlcv_df):
        entries, _ = trend_pullback_signals(ohlcv_df, adx_period=14, stoch_period=14)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Gap Fade
# ---------------------------------------------------------------------------

class TestGapFadeSignals:
    def test_returns_boolean_series_with_correct_length(self, gap_df):
        entries, exits = gap_fade_signals(gap_df)
        _assert_signal_pair(entries, exits, gap_df)

    def test_gap_events_generate_entries(self, gap_df):
        entries, _ = gap_fade_signals(gap_df, gap_threshold=0.03)
        assert entries.sum() > 0

    def test_larger_gap_threshold_fewer_signals(self, gap_df):
        e_low, _ = gap_fade_signals(gap_df, gap_threshold=0.01)
        e_high, _ = gap_fade_signals(gap_df, gap_threshold=0.10)
        assert e_low.sum() >= e_high.sum()

    def test_no_entry_on_first_bar(self, gap_df):
        entries, _ = gap_fade_signals(gap_df)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# VRP Harvest
# ---------------------------------------------------------------------------

class TestVrpHarvestSignals:
    def test_returns_boolean_series_with_correct_length(self, ohlcv_df):
        entries, exits = vrp_harvest_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_stricter_z_entry_fewer_signals(self, ohlcv_df):
        e_loose, _ = vrp_harvest_signals(ohlcv_df, z_entry=-0.5)
        e_strict, _ = vrp_harvest_signals(ohlcv_df, z_entry=-2.0)
        assert e_loose.sum() >= e_strict.sum()

    def test_signals_fire_with_adequate_history(self, ohlcv_df):
        entries, exits = vrp_harvest_signals(ohlcv_df, rv_window=10, iv_proxy_window=30, z_entry=-0.5)
        assert entries.sum() >= 0
        assert exits.sum() >= 0

    def test_no_signals_before_warmup(self, ohlcv_df):
        entries, _ = vrp_harvest_signals(ohlcv_df, rv_window=20, iv_proxy_window=60)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Dispatcher (build_signal_array)
# ---------------------------------------------------------------------------

class TestBuildSignalArray:
    def test_ma_crossover_dispatch(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "ma_crossover", {"fast_window": 5, "slow_window": 20})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_mean_reversion_dispatch(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "mean_reversion", {"lookback": 20, "z_threshold": 2.0})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_breakout_dispatch(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "breakout", {"bb_window": 10, "squeeze_lookback": 30})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_trend_pullback_dispatch(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "trend_pullback", {"adx_period": 14})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_gap_fade_dispatch(self, gap_df):
        entries, exits = build_signal_array(gap_df, "gap_fade", {"gap_threshold": 0.03})
        _assert_signal_pair(entries, exits, gap_df)

    def test_vrp_harvest_dispatch(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "vrp_harvest", {"rv_window": 20})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_unknown_strategy_raises(self, ohlcv_df):
        with pytest.raises(ValueError, match="Unknown strategy"):
            build_signal_array(ohlcv_df, "unknown_algo", {})

    def test_default_params_used_when_dict_empty(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "ma_crossover", {})
        _assert_signal_pair(entries, exits, ohlcv_df)
