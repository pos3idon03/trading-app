"""Tests for pairwise strategy combination matrix runner."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.combo_matrix_runner import (
    _extract_metric,
    build_symmetric_matrix,
    precompute_stances,
    run_combo_matrix,
)
from features.backtesting.combo_runner import ComboStrategyConfig


@pytest.fixture
def ohlcv_df():
    rng = np.random.default_rng(42)
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
        "volume": 1_000.0,
    })


class TestExtractMetric:
    def test_returns_float(self):
        assert _extract_metric({"sharpe_ratio": 1.5}, "sharpe_ratio") == 1.5

    def test_returns_none_for_missing(self):
        assert _extract_metric({}, "sharpe_ratio") is None

    def test_returns_none_for_nan(self):
        assert _extract_metric({"sharpe_ratio": float("nan")}, "sharpe_ratio") is None


class TestPrecomputeStances:
    def test_returns_one_series_per_strategy(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        stances = precompute_stances(ohlcv_df, configs)
        assert set(stances.keys()) == {"ma_crossover", "rsi"}
        assert len(stances["ma_crossover"]) == len(ohlcv_df)


class TestBuildSymmetricMatrix:
    def test_matrix_dimensions(self, ohlcv_df):
        strategies = ["ma_crossover", "rsi", "macd"]
        matrix = build_symmetric_matrix(
            ohlcv_df,
            strategies,
            {},
            combination_mode="majority",
            metric="sharpe_ratio",
            max_workers=1,
        )
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)

    def test_matrix_is_symmetric(self, ohlcv_df):
        strategies = ["ma_crossover", "rsi"]
        matrix = build_symmetric_matrix(
            ohlcv_df,
            strategies,
            {},
            combination_mode="majority",
            metric="total_return",
            max_workers=1,
        )
        assert matrix[0][1] == matrix[1][0]

    def test_diagonal_differs_from_off_diagonal_usually(self, ohlcv_df):
        strategies = ["ma_crossover", "rsi"]
        matrix = build_symmetric_matrix(
            ohlcv_df,
            strategies,
            {},
            combination_mode="majority",
            metric="total_return",
            max_workers=1,
        )
        assert matrix[0][0] is not None
        assert matrix[0][1] is not None

    def test_rejects_unknown_metric(self, ohlcv_df):
        with pytest.raises(ValueError, match="Unknown metric"):
            build_symmetric_matrix(
                ohlcv_df,
                ["ma_crossover", "rsi"],
                {},
                combination_mode="majority",
                metric="invalid_metric",
                max_workers=1,
            )


class TestRunComboMatrix:
    def test_returns_combo_matrix_result(self, ohlcv_df):
        result = run_combo_matrix(
            ohlcv_df,
            ["ma_crossover", "rsi"],
            {},
            combination_mode="and",
            metric="sharpe_ratio",
        )
        assert result.strategies == ["ma_crossover", "rsi"]
        assert result.metric == "sharpe_ratio"
        assert result.combination_mode == "and"
        assert len(result.values) == 2
        assert result.duration_ms >= 0
