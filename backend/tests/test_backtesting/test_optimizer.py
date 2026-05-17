"""Tests for walk-forward optimizer: param generation, splitting, and full optimization run."""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from features.backtesting.optimizer import (
    NO_FEASIBLE_MSG,
    _select_best_combo,
    generate_param_combinations,
    split_timeseries,
    walk_forward_optimize,
)
from features.backtesting.runner import BacktestResult


# ---------------------------------------------------------------------------
# generate_param_combinations
# ---------------------------------------------------------------------------


class TestGenerateParamCombinations:
    def test_single_param(self):
        combos = generate_param_combinations({"fast_window": [5, 10, 20]})
        assert len(combos) == 3
        assert combos[0] == {"fast_window": 5}

    def test_two_params_cartesian(self):
        combos = generate_param_combinations({"a": [1, 2], "b": [10, 20]})
        assert len(combos) == 4
        assert {"a": 1, "b": 10} in combos
        assert {"a": 2, "b": 20} in combos

    def test_empty_grid_returns_one_empty_combo(self):
        combos = generate_param_combinations({})
        assert combos == [{}]

    def test_preserves_param_names(self):
        combos = generate_param_combinations({"fast_window": [10], "slow_window": [50]})
        assert combos[0].keys() == {"fast_window", "slow_window"}


# ---------------------------------------------------------------------------
# split_timeseries
# ---------------------------------------------------------------------------


class TestSplitTimeseries:
    def _make_df(self, n: int) -> pd.DataFrame:
        return pd.DataFrame({"close": range(n)})

    def test_returns_n_splits(self):
        df = self._make_df(100)
        splits = split_timeseries(df, 5)
        assert len(splits) == 5

    def test_each_split_has_train_and_test(self):
        df = self._make_df(60)
        splits = split_timeseries(df, 2)
        for train, test in splits:
            assert not train.empty
            assert not test.empty

    def test_train_grows_each_fold(self):
        df = self._make_df(100)
        splits = split_timeseries(df, 4)
        train_sizes = [len(t) for t, _ in splits]
        assert train_sizes == sorted(train_sizes)

    def test_no_overlap_between_train_and_test(self):
        df = self._make_df(100)
        splits = split_timeseries(df, 3)
        for train, test in splits:
            train_idx = set(train.index)
            test_idx = set(test.index)
            assert train_idx.isdisjoint(test_idx)

    def test_insufficient_data_returns_empty(self):
        df = self._make_df(2)
        splits = split_timeseries(df, 5)
        assert splits == []


# ---------------------------------------------------------------------------
# walk_forward_optimize (unit — patched run_backtest)
# ---------------------------------------------------------------------------


def _make_price_df(n: int = 300) -> pd.DataFrame:
    """Return a full OHLCV DataFrame compatible with all strategies."""
    rng = np.random.default_rng(42)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)))
    high = close + rng.uniform(0.0, 1.0, n)
    low = close - rng.uniform(0.0, 1.0, n)
    open_p = close.shift(1).fillna(close.iloc[0])
    volume = pd.Series(rng.integers(100_000, 500_000, n).astype(float))
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"time": dates, "open": open_p.values, "high": high.values,
         "low": low.values, "close": close.values, "volume": volume.values},
    )


class TestWalkForwardOptimize:
    def test_returns_optimization_result(self):
        df = _make_price_df()
        result = walk_forward_optimize(
            df,
            strategy="ma_crossover",
            param_grid={"fast_window": [5, 10], "slow_window": [20, 50]},
            n_splits=2,
        )
        assert result.best_params is not None
        assert isinstance(result.best_sharpe, float)
        assert result.n_splits == 2

    def test_best_params_are_from_grid(self):
        df = _make_price_df()
        grid = {"fast_window": [5, 10], "slow_window": [20, 50]}
        result = walk_forward_optimize(df, strategy="ma_crossover", param_grid=grid, n_splits=2)
        assert result.best_params["fast_window"] in [5, 10]
        assert result.best_params["slow_window"] in [20, 50]

    def test_all_results_contains_every_combo(self):
        df = _make_price_df()
        grid = {"fast_window": [5, 10], "slow_window": [20, 50]}
        result = walk_forward_optimize(df, strategy="ma_crossover", param_grid=grid, n_splits=2)
        assert len(result.all_results) == 4

    def test_raises_on_insufficient_data(self):
        df = pd.DataFrame({"time": pd.date_range("2020-01-01", periods=3, freq="D"), "close": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError, match="Insufficient data"):
            walk_forward_optimize(df, strategy="ma_crossover", param_grid={"fast_window": [5]}, n_splits=5)

    def test_mean_reversion_strategy(self):
        df = _make_price_df(400)
        result = walk_forward_optimize(
            df,
            strategy="mean_reversion",
            param_grid={"lookback": [10, 20], "z_threshold": [1.5, 2.0]},
            n_splits=2,
        )
        assert result.best_params["lookback"] in [10, 20]
        assert result.best_params["z_threshold"] in [1.5, 2.0]

    def test_breakout_strategy(self):
        df = _make_price_df(500)
        result = walk_forward_optimize(
            df,
            strategy="breakout",
            param_grid={"bb_window": [10, 15], "squeeze_lookback": [30, 60], "donchian_window": [10, 15]},
            n_splits=2,
        )
        assert result.best_params["bb_window"] in [10, 15]
        assert isinstance(result.best_sharpe, float)

    def test_trend_pullback_strategy(self):
        df = _make_price_df(500)
        result = walk_forward_optimize(
            df,
            strategy="trend_pullback",
            param_grid={"adx_period": [10, 14], "adx_threshold": [20.0, 25.0]},
            n_splits=2,
        )
        assert result.best_params["adx_period"] in [10, 14]
        assert isinstance(result.best_sharpe, float)

    def test_vrp_harvest_strategy(self):
        df = _make_price_df(500)
        result = walk_forward_optimize(
            df,
            strategy="vrp_harvest",
            param_grid={"rv_window": [10, 20], "iv_proxy_window": [40, 60]},
            n_splits=2,
        )
        assert result.best_params["rv_window"] in [10, 20]
        assert isinstance(result.best_sharpe, float)


class TestDrawdownCapSelection:
    def test_select_best_combo_respects_cap(self):
        avg_scores = {0: 2.5, 1: 1.2}
        avg_drawdowns = {0: -0.35, 1: -0.15}
        combo_scores = {0: [2.5], 1: [1.2]}
        best = _select_best_combo(avg_scores, avg_drawdowns, combo_scores, -0.25)
        assert best == 1

    def test_select_best_combo_without_cap_picks_highest_metric(self):
        avg_scores = {0: 2.5, 1: 1.2}
        avg_drawdowns = {0: -0.35, 1: -0.15}
        combo_scores = {0: [2.5], 1: [1.2]}
        best = _select_best_combo(avg_scores, avg_drawdowns, combo_scores, None)
        assert best == 0

    def test_no_feasible_raises(self):
        avg_scores = {0: 2.5}
        avg_drawdowns = {0: -0.50}
        combo_scores = {0: [2.5]}
        with pytest.raises(ValueError, match=NO_FEASIBLE_MSG):
            _select_best_combo(avg_scores, avg_drawdowns, combo_scores, -0.25)


class TestWalkForwardDrawdownCapIntegration:
    def _bt(self, sortino: float, drawdown: float) -> BacktestResult:
        return BacktestResult(
            metrics={"sortino_ratio": sortino, "max_drawdown": drawdown},
            equity_curve=[],
            trade_log=[],
            buy_hold_curve=[],
            indicator_series=[],
            duration_ms=1.0,
        )

    def test_all_results_include_avg_drawdown(self):
        df = _make_price_df(300)
        with patch(
            "features.backtesting.optimizer.run_backtest",
            return_value=self._bt(1.5, -0.10),
        ):
            result = walk_forward_optimize(
                df,
                strategy="ma_crossover",
                param_grid={"fast_window": [5, 10]},
                n_splits=2,
                optimize_metric="sortino_ratio",
            )
        assert all("avg_oos_max_drawdown" in row for row in result.all_results)
        assert result.best_avg_oos_max_drawdown is not None
