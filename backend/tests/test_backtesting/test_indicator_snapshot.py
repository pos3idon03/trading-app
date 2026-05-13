"""Tests for indicator_snapshot: INDICATOR_MAP entries and compute_monthly_breakdown."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.combo_runner import ComboStrategyConfig
from features.backtesting.indicator_snapshot import (
    INDICATOR_MAP,
    _safe_float,
    compute_monthly_breakdown,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ohlcv_df():
    """2-year daily OHLCV DataFrame with sufficient depth for all indicators."""
    rng = np.random.default_rng(0)
    n = 504  # ~2 years
    returns = rng.normal(0.0005, 0.012, n)
    close = pd.Series(100.0 * np.cumprod(1 + returns))
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "time": dates,
        "open": close.values,
        "high": close.values * 1.007,
        "low": close.values * 0.993,
        "close": close.values,
        "volume": rng.integers(500_000, 2_000_000, n).astype(float),
    })


@pytest.fixture
def short_ohlcv_df():
    """Short OHLCV DataFrame spanning ~4 months (for monthly resampling tests)."""
    rng = np.random.default_rng(7)
    n = 120
    returns = rng.normal(0.001, 0.01, n)
    close = pd.Series(50.0 * np.cumprod(1 + returns))
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "time": dates,
        "open": close.values,
        "high": close.values * 1.005,
        "low": close.values * 0.995,
        "close": close.values,
        "volume": 1_000_000.0,
    })


@pytest.fixture
def two_strategy_configs():
    return [
        ComboStrategyConfig(strategy_name="ma_crossover", strategy_params={}, weight=1.0),
        ComboStrategyConfig(strategy_name="rsi", strategy_params={}, weight=1.0),
    ]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_finite_value_rounds(self):
        assert _safe_float(3.14159) == 3.14

    def test_nan_returns_none(self):
        assert _safe_float(float("nan")) is None

    def test_inf_returns_none(self):
        assert _safe_float(float("inf")) is None

    def test_non_numeric_returns_none(self):
        assert _safe_float("abc") is None

    def test_none_returns_none(self):
        assert _safe_float(None) is None


# ---------------------------------------------------------------------------
# INDICATOR_MAP spot checks
# ---------------------------------------------------------------------------

class TestIndicatorMapColumns:
    """Verify each spot-checked indicator function returns the expected columns."""

    def _run(self, name, df, params=None):
        fn = INDICATOR_MAP[name]
        return fn(df, params or {})

    def test_ma_crossover_columns(self, ohlcv_df):
        result = self._run("ma_crossover", ohlcv_df)
        assert "fast_ma" in result.columns
        assert "slow_ma" in result.columns

    def test_rsi_columns(self, ohlcv_df):
        result = self._run("rsi", ohlcv_df)
        assert "rsi" in result.columns

    def test_macd_columns(self, ohlcv_df):
        result = self._run("macd", ohlcv_df)
        assert "macd" in result.columns
        assert "signal" in result.columns

    def test_aroon_columns(self, ohlcv_df):
        result = self._run("aroon", ohlcv_df)
        assert "aroon_up" in result.columns
        assert "aroon_down" in result.columns

    def test_stoch_rsi_columns(self, ohlcv_df):
        result = self._run("stoch_rsi", ohlcv_df)
        assert "stoch_k" in result.columns
        assert "stoch_d" in result.columns

    def test_breakout_columns(self, ohlcv_df):
        result = self._run("breakout", ohlcv_df)
        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns
        assert "donchian_high" in result.columns
        assert "donchian_low" in result.columns

    def test_mean_reversion_columns(self, ohlcv_df):
        result = self._run("mean_reversion", ohlcv_df)
        assert "z_score" in result.columns

    def test_range_breakout_columns(self, ohlcv_df):
        result = self._run("range_breakout", ohlcv_df)
        assert "range_high" in result.columns
        assert "range_low" in result.columns

    def test_vwap_columns(self, ohlcv_df):
        result = self._run("vwap_cross", ohlcv_df)
        assert "vwap" in result.columns

    def test_vrp_harvest_columns(self, ohlcv_df):
        result = self._run("vrp_harvest", ohlcv_df)
        assert "vrp_z" in result.columns

    def test_empty_strategies_return_empty_df(self, ohlcv_df):
        for name in ("gap_fade", "orb", "seasonal"):
            result = INDICATOR_MAP[name](ohlcv_df, {})
            assert result.empty or len(result.columns) == 0

    def test_all_strategies_covered(self):
        required = {
            "ma_crossover", "sma_cross", "ema_cross", "sma_break", "macd",
            "rsi", "lrsi", "aroon", "stoch_rsi", "momentum_rotation",
            "new_high_low", "atr_trailing_stop", "vwap_cross", "grid_trading",
            "wedge_compression", "mean_reversion", "mean_reversion_trend",
            "mean_reversion_range", "reverting_market", "breakout",
            "range_breakout", "trend_pullback", "vrp_harvest",
            "orb", "gap_fade", "seasonal",
        }
        assert required.issubset(set(INDICATOR_MAP.keys()))

    def test_result_length_matches_df(self, ohlcv_df):
        for name in ("ma_crossover", "rsi", "macd", "mean_reversion"):
            result = INDICATOR_MAP[name](ohlcv_df, {})
            assert len(result) == len(ohlcv_df)


# ---------------------------------------------------------------------------
# compute_monthly_breakdown
# ---------------------------------------------------------------------------

class TestComputeMonthlyBreakdown:
    def test_returns_one_row_per_calendar_month(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        # 120 days from 2022-01-01 spans Jan–Apr (4 months)
        assert len(rows) >= 3
        assert len(rows) <= 5

    def test_month_format(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        for row in rows:
            assert len(row["month"]) == 7  # "YYYY-MM"
            assert row["month"][4] == "-"

    def test_months_are_sorted(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        months = [r["month"] for r in rows]
        assert months == sorted(months)

    def test_position_values_are_buy_or_sell(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        valid = {"Buy", "Sell"}
        for row in rows:
            assert row["combined_position"] in valid
            for s in row["strategies"]:
                assert s["position"] in valid

    def test_position_values_never_hold(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        for row in rows:
            assert row["combined_position"] != "Hold"
            for s in row["strategies"]:
                assert s["position"] != "Hold"

    def test_each_row_has_all_strategies(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        for row in rows:
            assert len(row["strategies"]) == 2
            names = {s["strategy_name"] for s in row["strategies"]}
            assert names == {"ma_crossover", "rsi"}

    def test_indicator_values_finite_or_none(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        for row in rows:
            for s in row["strategies"]:
                for val in s["indicators"].values():
                    if val is not None:
                        assert np.isfinite(val)

    def test_and_mode(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "and")
        assert isinstance(rows, list)
        assert all("combined_position" in r for r in rows)

    def test_weighted_mode(self, short_ohlcv_df):
        configs = [
            ComboStrategyConfig(strategy_name="ma_crossover", strategy_params={}, weight=0.7),
            ComboStrategyConfig(strategy_name="rsi", strategy_params={}, weight=0.3),
        ]
        rows = compute_monthly_breakdown(short_ohlcv_df, configs, "weighted", threshold=0.5)
        assert isinstance(rows, list)
        assert len(rows) > 0

    def test_rsi_indicators_present(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        for row in rows:
            rsi_state = next(s for s in row["strategies"] if s["strategy_name"] == "rsi")
            assert "rsi" in rsi_state["indicators"]

    def test_ma_crossover_indicators_present(self, short_ohlcv_df, two_strategy_configs):
        rows = compute_monthly_breakdown(short_ohlcv_df, two_strategy_configs, "majority")
        for row in rows:
            ma_state = next(s for s in row["strategies"] if s["strategy_name"] == "ma_crossover")
            assert "fast_ma" in ma_state["indicators"]
            assert "slow_ma" in ma_state["indicators"]
