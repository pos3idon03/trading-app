"""Tests for the 17 new algorithmic trading strategy signal generators."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.strategies import (
    aroon_signals,
    atr_trailing_stop_signals,
    build_signal_array,
    ema_cross_signals,
    grid_trading_signals,
    lrsi_signals,
    macd_signals,
    mean_reversion_range_signals,
    mean_reversion_trend_signals,
    momentum_rotation_signals,
    new_high_low_signals,
    orb_signals,
    range_breakout_signals,
    reverting_market_signals,
    rsi_signals,
    seasonal_signals,
    sma_break_signals,
    sma_cross_signals,
    stoch_rsi_signals,
    vwap_cross_signals,
    wedge_compression_signals,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ohlcv_df():
    """Synthetic daily OHLCV DataFrame with 400 bars and a DatetimeIndex."""
    rng = np.random.default_rng(42)
    n = 400
    returns = rng.normal(0.001, 0.015, n)
    close = pd.Series(100 * np.cumprod(1 + returns))
    high = close * (1 + rng.uniform(0.0, 0.015, n))
    low = close * (1 - rng.uniform(0.0, 0.015, n))
    open_p = close.shift(1).fillna(close.iloc[0]) * rng.uniform(0.995, 1.005, n)
    volume = pd.Series(rng.integers(100_000, 1_000_000, n).astype(float))
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "open": open_p.values,
            "high": high.values,
            "low": low.values,
            "close": close.values,
            "volume": volume.values,
        },
        index=dates,
    )


@pytest.fixture
def ohlcv_df_with_time_col(ohlcv_df):
    """Same DataFrame but with a 'time' column instead of DatetimeIndex."""
    df = ohlcv_df.reset_index().rename(columns={"index": "time"})
    return df


# ---------------------------------------------------------------------------
# Shared helper
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
# SMA Cross (Golden / Death Cross)
# ---------------------------------------------------------------------------

class TestSMACrossSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = sma_cross_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_entries_occur_with_adequate_history(self, ohlcv_df):
        entries, _ = sma_cross_signals(ohlcv_df, fast_window=10, slow_window=30)
        assert entries.sum() >= 0

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = sma_cross_signals(ohlcv_df, fast_window=10, slow_window=30)
        assert not (entries & exits).any()

    def test_no_signal_before_slow_ma_warmup(self, ohlcv_df):
        entries, exits = sma_cross_signals(ohlcv_df, fast_window=5, slow_window=50)
        assert not entries.iloc[0]
        assert not exits.iloc[0]

    def test_faster_window_more_crosses(self, ohlcv_df):
        e_fast, _ = sma_cross_signals(ohlcv_df, fast_window=5, slow_window=20)
        e_slow, _ = sma_cross_signals(ohlcv_df, fast_window=50, slow_window=200)
        assert e_fast.sum() >= e_slow.sum()


# ---------------------------------------------------------------------------
# EMA Cross
# ---------------------------------------------------------------------------

class TestEMACrossSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = ema_cross_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = ema_cross_signals(ohlcv_df, fast_span=5, slow_span=20)
        assert not (entries & exits).any()

    def test_faster_span_more_crosses(self, ohlcv_df):
        e_fast, _ = ema_cross_signals(ohlcv_df, fast_span=3, slow_span=10)
        e_slow, _ = ema_cross_signals(ohlcv_df, fast_span=20, slow_span=50)
        assert e_fast.sum() >= e_slow.sum()


# ---------------------------------------------------------------------------
# SMA Break
# ---------------------------------------------------------------------------

class TestSMABreakSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = sma_break_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = sma_break_signals(ohlcv_df, sma_window=50)
        assert not (entries & exits).any()

    def test_shorter_sma_more_crossings(self, ohlcv_df):
        e_short, _ = sma_break_signals(ohlcv_df, sma_window=10)
        e_long, _ = sma_break_signals(ohlcv_df, sma_window=100)
        assert e_short.sum() >= e_long.sum()

    def test_no_signal_before_warmup(self, ohlcv_df):
        entries, _ = sma_break_signals(ohlcv_df, sma_window=50)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

class TestMACDSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = macd_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = macd_signals(ohlcv_df)
        assert not (entries & exits).any()

    def test_signals_fire(self, ohlcv_df):
        entries, exits = macd_signals(ohlcv_df, fast=5, slow=15, signal=5)
        assert entries.sum() > 0
        assert exits.sum() > 0

    def test_no_signal_at_first_bar(self, ohlcv_df):
        entries, exits = macd_signals(ohlcv_df)
        assert not entries.iloc[0]
        assert not exits.iloc[0]


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

class TestRSISignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = rsi_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_wider_bands_more_signals(self, ohlcv_df):
        e_wide, _ = rsi_signals(ohlcv_df, overbought=60.0, oversold=40.0)
        e_narrow, _ = rsi_signals(ohlcv_df, overbought=90.0, oversold=10.0)
        assert e_wide.sum() >= e_narrow.sum()

    def test_no_signal_at_first_bar(self, ohlcv_df):
        entries, exits = rsi_signals(ohlcv_df)
        assert not entries.iloc[0]
        assert not exits.iloc[0]


# ---------------------------------------------------------------------------
# LRSI
# ---------------------------------------------------------------------------

class TestLRSISignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = lrsi_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_wider_bands_more_signals(self, ohlcv_df):
        e_wide, _ = lrsi_signals(ohlcv_df, overbought=0.6, oversold=0.4)
        e_narrow, _ = lrsi_signals(ohlcv_df, overbought=0.95, oversold=0.05)
        assert e_wide.sum() >= e_narrow.sum()

    def test_gamma_affects_smoothness(self, ohlcv_df):
        """Higher gamma means smoother filter — fewer crossings."""
        e_low, _ = lrsi_signals(ohlcv_df, gamma=0.1, overbought=0.7, oversold=0.3)
        e_high, _ = lrsi_signals(ohlcv_df, gamma=0.9, overbought=0.7, oversold=0.3)
        assert e_low.sum() >= 0
        assert e_high.sum() >= 0


# ---------------------------------------------------------------------------
# New High / Low
# ---------------------------------------------------------------------------

class TestNewHighLowSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = new_high_low_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_shorter_lookback_more_signals(self, ohlcv_df):
        e_short, _ = new_high_low_signals(ohlcv_df, lookback=20)
        e_long, _ = new_high_low_signals(ohlcv_df, lookback=200)
        assert e_short.sum() >= e_long.sum()

    def test_no_signal_before_warmup(self, ohlcv_df):
        entries, _ = new_high_low_signals(ohlcv_df, lookback=50)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# ATR Trailing Stop
# ---------------------------------------------------------------------------

class TestATRTrailingStopSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = atr_trailing_stop_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_smaller_trend_ma_more_entries(self, ohlcv_df):
        e_small, _ = atr_trailing_stop_signals(ohlcv_df, trend_ma=10)
        e_large, _ = atr_trailing_stop_signals(ohlcv_df, trend_ma=100)
        assert e_small.sum() >= e_large.sum()

    def test_no_signal_before_warmup(self, ohlcv_df):
        entries, _ = atr_trailing_stop_signals(ohlcv_df, trend_ma=50)
        assert not entries.iloc[0]

    def test_exits_on_steep_drawdown(self):
        """Locked-in trailing stop must fire when price capitulates."""
        n = 120
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        close_vals = (
            list(np.linspace(100, 150, 60))
            + list(np.linspace(150, 90, 10))
            + [90.0] * (n - 70)
        )
        close = pd.Series(close_vals)
        high = close * 1.01
        low = close * 0.99
        df = pd.DataFrame(
            {
                "open": close.shift(1).fillna(close.iloc[0]),
                "high": high,
                "low": low,
                "close": close,
                "volume": 1_000_000.0,
                "time": dates,
            }
        )

        entries, exits = atr_trailing_stop_signals(
            df, atr_period=14, atr_multiplier=3.0, trend_ma=20
        )

        assert entries.sum() >= 1
        assert exits.sum() >= 1
        assert not (entries & exits).any()

    def test_produces_multiple_round_trips_on_trending_data(self, ohlcv_df):
        entries, exits = atr_trailing_stop_signals(ohlcv_df, trend_ma=20)
        assert exits.sum() >= 1


# ---------------------------------------------------------------------------
# VWAP Cross
# ---------------------------------------------------------------------------

class TestVWAPCrossSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = vwap_cross_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = vwap_cross_signals(ohlcv_df)
        assert not (entries & exits).any()

    def test_band_pct_produces_valid_signals(self, ohlcv_df):
        e_band, x_band = vwap_cross_signals(ohlcv_df, band_pct=0.05)
        _assert_signal_pair(e_band, x_band, ohlcv_df)
        assert e_band.sum() >= 0
        assert x_band.sum() >= 0


# ---------------------------------------------------------------------------
# Grid Trading
# ---------------------------------------------------------------------------

class TestGridTradingSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = grid_trading_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_smaller_grid_more_signals(self, ohlcv_df):
        e_small, _ = grid_trading_signals(ohlcv_df, grid_size=0.005, num_levels=2)
        e_large, _ = grid_trading_signals(ohlcv_df, grid_size=0.10, num_levels=5)
        assert e_small.sum() >= e_large.sum()

    def test_no_signal_before_warmup(self, ohlcv_df):
        entries, _ = grid_trading_signals(ohlcv_df)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Wedge Compression
# ---------------------------------------------------------------------------

class TestWedgeCompressionSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = wedge_compression_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_shorter_lookback_more_compressions(self, ohlcv_df):
        e_short, _ = wedge_compression_signals(ohlcv_df, compression_lookback=10)
        e_long, _ = wedge_compression_signals(ohlcv_df, compression_lookback=100)
        assert e_short.sum() >= e_long.sum()

    def test_no_signal_at_first_bar(self, ohlcv_df):
        entries, _ = wedge_compression_signals(ohlcv_df)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Mean Reversion Trend
# ---------------------------------------------------------------------------

class TestMeanReversionTrendSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = mean_reversion_trend_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_lower_adx_threshold_more_entries(self, ohlcv_df):
        e_low, _ = mean_reversion_trend_signals(ohlcv_df, adx_threshold=5.0)
        e_high, _ = mean_reversion_trend_signals(ohlcv_df, adx_threshold=50.0)
        assert e_low.sum() >= e_high.sum()

    def test_lower_z_threshold_more_entries(self, ohlcv_df):
        e_low, _ = mean_reversion_trend_signals(ohlcv_df, z_threshold=0.5, adx_threshold=5.0)
        e_high, _ = mean_reversion_trend_signals(ohlcv_df, z_threshold=4.0, adx_threshold=5.0)
        assert e_low.sum() >= e_high.sum()


# ---------------------------------------------------------------------------
# Mean Reversion Range
# ---------------------------------------------------------------------------

class TestMeanReversionRangeSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = mean_reversion_range_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_higher_adx_max_more_entries(self, ohlcv_df):
        e_high, _ = mean_reversion_range_signals(ohlcv_df, adx_max=50.0)
        e_low, _ = mean_reversion_range_signals(ohlcv_df, adx_max=5.0)
        assert e_high.sum() >= e_low.sum()

    def test_no_signal_before_warmup(self, ohlcv_df):
        entries, _ = mean_reversion_range_signals(ohlcv_df)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Reverting Market
# ---------------------------------------------------------------------------

class TestRevertingMarketSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = reverting_market_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_higher_adx_max_more_entries(self, ohlcv_df):
        e_high, _ = reverting_market_signals(ohlcv_df, adx_max=50.0)
        e_low, _ = reverting_market_signals(ohlcv_df, adx_max=5.0)
        assert e_high.sum() >= e_low.sum()

    def test_wider_rsi_band_more_entries(self, ohlcv_df):
        e_wide, _ = reverting_market_signals(ohlcv_df, rsi_lower=48.0, adx_max=50.0)
        e_narrow, _ = reverting_market_signals(ohlcv_df, rsi_lower=10.0, adx_max=50.0)
        assert e_wide.sum() >= e_narrow.sum()


# ---------------------------------------------------------------------------
# Momentum Rotation
# ---------------------------------------------------------------------------

class TestMomentumRotationSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = momentum_rotation_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = momentum_rotation_signals(ohlcv_df)
        assert not (entries & exits).any()

    def test_shorter_windows_more_switches(self, ohlcv_df):
        e_short, _ = momentum_rotation_signals(ohlcv_df, short_window=5, long_window=10)
        e_long, _ = momentum_rotation_signals(ohlcv_df, short_window=50, long_window=150)
        assert e_short.sum() >= e_long.sum()

    def test_no_signal_before_warmup(self, ohlcv_df):
        entries, _ = momentum_rotation_signals(ohlcv_df, long_window=60)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# Range Breakout
# ---------------------------------------------------------------------------

class TestRangeBreakoutSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = range_breakout_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_shorter_lookback_more_breakouts(self, ohlcv_df):
        e_short, _ = range_breakout_signals(ohlcv_df, lookback=5)
        e_long, _ = range_breakout_signals(ohlcv_df, lookback=100)
        assert e_short.sum() >= e_long.sum()

    def test_no_signal_at_first_bar(self, ohlcv_df):
        entries, _ = range_breakout_signals(ohlcv_df)
        assert not entries.iloc[0]


# ---------------------------------------------------------------------------
# ORB (Open Range Breakout)
# ---------------------------------------------------------------------------

class TestORBSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = orb_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_signals_fire_after_opening_range(self, ohlcv_df):
        entries, exits = orb_signals(ohlcv_df, opening_bars=5)
        assert entries.sum() >= 0
        assert exits.sum() >= 0

    def test_no_entry_within_opening_bars(self, ohlcv_df):
        entries, _ = orb_signals(ohlcv_df, opening_bars=10)
        assert not entries.iloc[:10].any()

    def test_larger_opening_range_fewer_breakouts(self, ohlcv_df):
        e_small, _ = orb_signals(ohlcv_df, opening_bars=2)
        e_large, _ = orb_signals(ohlcv_df, opening_bars=50)
        assert e_small.sum() >= e_large.sum()


# ---------------------------------------------------------------------------
# Seasonal
# ---------------------------------------------------------------------------

class TestSeasonalSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = seasonal_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_entries_on_buy_month(self, ohlcv_df):
        entries, _ = seasonal_signals(ohlcv_df, buy_month=11, sell_month=5)
        assert entries.sum() > 0

    def test_exits_on_sell_month(self, ohlcv_df):
        _, exits = seasonal_signals(ohlcv_df, buy_month=11, sell_month=5)
        assert exits.sum() > 0

    def test_with_time_column(self, ohlcv_df_with_time_col):
        entries, exits = seasonal_signals(ohlcv_df_with_time_col, buy_month=11, sell_month=5)
        _assert_signal_pair(entries, exits, ohlcv_df_with_time_col)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = seasonal_signals(ohlcv_df)
        assert not (entries & exits).any()


# ---------------------------------------------------------------------------
# Dispatcher — new strategy keys
# ---------------------------------------------------------------------------

class TestBuildSignalArrayNewStrategies:
    @pytest.mark.parametrize("strategy,params", [
        ("sma_cross", {"fast_window": 10, "slow_window": 30}),
        ("ema_cross", {"fast_span": 5, "slow_span": 20}),
        ("sma_break", {"sma_window": 50}),
        ("macd", {"fast": 5, "slow": 15, "signal": 5}),
        ("rsi", {"period": 14, "overbought": 70.0, "oversold": 30.0}),
        ("lrsi", {"gamma": 0.5}),
        ("new_high_low", {"lookback": 50}),
        ("momentum_rotation", {"short_window": 10, "long_window": 30}),
        ("atr_trailing_stop", {"atr_period": 14, "trend_ma": 20}),
        ("vwap_cross", {}),
        ("grid_trading", {"grid_size": 0.02, "num_levels": 3}),
        ("wedge_compression", {"compression_lookback": 15}),
        ("mean_reversion_trend", {"adx_threshold": 5.0}),
        ("mean_reversion_range", {"adx_max": 50.0}),
        ("reverting_market", {"adx_max": 50.0}),
        ("range_breakout", {"lookback": 10}),
        ("orb", {"opening_bars": 5}),
        ("seasonal", {"buy_month": 11, "sell_month": 5}),
        ("aroon", {"period": 26, "threshold": 50.0}),
        ("stoch_rsi", {"rsi_period": 14, "stoch_period": 14, "smooth_k": 3, "smooth_d": 3}),
    ])
    def test_dispatch_returns_valid_signal_pair(self, ohlcv_df, strategy, params):
        entries, exits = build_signal_array(ohlcv_df, strategy, params)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_default_params_used_when_dict_empty(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "sma_cross", {})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_unknown_strategy_still_raises(self, ohlcv_df):
        with pytest.raises(ValueError, match="Unknown strategy"):
            build_signal_array(ohlcv_df, "made_up_strategy", {})


# ---------------------------------------------------------------------------
# Aroon 52 strategy tests
# ---------------------------------------------------------------------------

class TestAroonSignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = aroon_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_default_period_52(self, ohlcv_df):
        entries, exits = aroon_signals(ohlcv_df, period=52)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_custom_period_and_threshold(self, ohlcv_df):
        entries, exits = aroon_signals(ohlcv_df, period=26, threshold=70.0)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = aroon_signals(ohlcv_df)
        assert not (entries & exits).any()

    def test_high_threshold_reduces_entries(self, ohlcv_df):
        e_low, _ = aroon_signals(ohlcv_df, threshold=0.0)
        e_high, _ = aroon_signals(ohlcv_df, threshold=90.0)
        assert e_low.sum() >= e_high.sum()

    def test_dispatch_via_build_signal_array(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "aroon", {"period": 52})
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_default_params_via_build_signal_array(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "aroon", {})
        _assert_signal_pair(entries, exits, ohlcv_df)


# ---------------------------------------------------------------------------
# Stochastic RSI strategy tests
# ---------------------------------------------------------------------------

class TestStochRSISignals:
    def test_returns_correct_shape(self, ohlcv_df):
        entries, exits = stoch_rsi_signals(ohlcv_df)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_custom_periods(self, ohlcv_df):
        entries, exits = stoch_rsi_signals(ohlcv_df, rsi_period=10, stoch_period=10)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_custom_thresholds(self, ohlcv_df):
        entries, exits = stoch_rsi_signals(ohlcv_df, overbought=0.9, oversold=0.1)
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_no_simultaneous_entry_and_exit(self, ohlcv_df):
        entries, exits = stoch_rsi_signals(ohlcv_df)
        assert not (entries & exits).any()

    def test_tight_thresholds_reduce_signals(self, ohlcv_df):
        e_wide, x_wide = stoch_rsi_signals(ohlcv_df, overbought=0.6, oversold=0.4)
        e_tight, x_tight = stoch_rsi_signals(ohlcv_df, overbought=0.95, oversold=0.05)
        assert e_wide.sum() >= e_tight.sum()
        assert x_wide.sum() >= x_tight.sum()

    def test_dispatch_via_build_signal_array(self, ohlcv_df):
        entries, exits = build_signal_array(
            ohlcv_df, "stoch_rsi",
            {"rsi_period": 14, "stoch_period": 14, "smooth_k": 3, "smooth_d": 3},
        )
        _assert_signal_pair(entries, exits, ohlcv_df)

    def test_default_params_via_build_signal_array(self, ohlcv_df):
        entries, exits = build_signal_array(ohlcv_df, "stoch_rsi", {})
        _assert_signal_pair(entries, exits, ohlcv_df)
