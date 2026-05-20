"""Tests for multi-timeframe combo signal alignment."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.combo_runner import ComboStrategyConfig, run_combo_backtest
from features.backtesting.multi_timeframe_combo import (
    align_stance_to_execution,
    build_multi_tf_combo_signals,
    combo_data_load_timeframe,
    resample_ohlcv_df,
)


@pytest.fixture
def hourly_base_df():
    """120 hourly bars for resampling tests."""
    rng = np.random.default_rng(7)
    n = 120
    returns = rng.normal(0.0005, 0.005, n)
    close = pd.Series(100.0 * np.cumprod(1 + returns))
    dates = pd.date_range("2022-01-01", periods=n, freq="h")
    return pd.DataFrame({
        "time": dates,
        "open": close.values,
        "high": close.values * 1.002,
        "low": close.values * 0.998,
        "close": close.values,
        "volume": 10_000.0,
    })


class TestComboDataLoadTimeframe:
    def test_picks_finest_among_execution_and_legs(self):
        assert combo_data_load_timeframe("1d", ["4h", "30m"]) == "30m"
        assert combo_data_load_timeframe("1h", ["1h", "4h"]) == "1h"


class TestResampleOhlcvDf:
    def test_downsamples_hourly_to_4h(self, hourly_base_df):
        out = resample_ohlcv_df(hourly_base_df, "4h")
        assert len(out) < len(hourly_base_df)
        assert len(out) >= 20


class TestAlignStanceToExecution:
    def test_forward_fills_coarser_leg_onto_exec_grid(self, hourly_base_df):
        leg_df = resample_ohlcv_df(hourly_base_df, "4h")
        exec_df = resample_ohlcv_df(hourly_base_df, "1h")
        stance = pd.Series(["Buy"] * len(leg_df), index=leg_df.index)
        aligned = align_stance_to_execution(stance, leg_df, exec_df)
        assert len(aligned) == len(exec_df)


class TestBuildMultiTfComboSignals:
    def test_produces_entry_exit_series(self, hourly_base_df):
        configs = [
            ComboStrategyConfig("rsi", {"period": 14}, timeframe="4h"),
            ComboStrategyConfig("macd", {"fast": 12, "slow": 26, "signal": 9}, timeframe="1h"),
        ]
        entries, exits = build_multi_tf_combo_signals(
            hourly_base_df, configs, "1h", "majority", 0.5,
        )
        exec_df = resample_ohlcv_df(hourly_base_df, "1h")
        assert len(entries) == len(exec_df)
        assert len(exits) == len(exec_df)


class TestRunComboBacktestMultiTf:
    def test_runs_with_mixed_leg_timeframes(self, hourly_base_df):
        configs = [
            ComboStrategyConfig("rsi", {"period": 14}, timeframe="4h"),
            ComboStrategyConfig("macd", {"fast": 12, "slow": 26, "signal": 9}, timeframe="1h"),
        ]
        result = run_combo_backtest(
            hourly_base_df,
            strategies=configs,
            combination_mode="majority",
            timeframe="1h",
        )
        assert result.metrics is not None
        assert len(result.equity_curve) > 0
