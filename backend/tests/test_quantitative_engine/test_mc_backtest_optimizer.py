"""Tests for MC backtest walk-forward optimizer."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.quantitative_engine.mc_backtest_optimizer import (
    compute_total_steps,
    validate_param_grid,
    walk_forward_mc_backtest_optimize_async,
    _normalize_threshold,
)


class TestValidateParamGrid:
    def test_filters_invalid_threshold_order(self):
        grid = {
            "buy_threshold": [40],
            "sell_threshold": [60],
        }
        with pytest.raises(ValueError, match="No valid parameter combinations"):
            validate_param_grid(grid)

    def test_accepts_percent_thresholds(self):
        grid = {
            "buy_threshold": [55],
            "sell_threshold": [48],
            "num_paths": [500],
        }
        combos = validate_param_grid(grid)
        assert len(combos) == 1
        assert combos[0]["buy_threshold"] == pytest.approx(0.55)

    def test_accepts_calibration_days_and_filters(self):
        grid = {
            "buy_threshold": [55],
            "sell_threshold": [48],
            "calibration_days": [14],
            "entry_confirmation_bars": [2],
            "prob_smoothing_bars": [3],
        }
        combos = validate_param_grid(grid)
        assert combos[0]["calibration_days"] == 14
        assert combos[0]["entry_confirmation_bars"] == 2

    def test_normalizes_threshold(self):
        assert _normalize_threshold(55) == pytest.approx(0.55)
        assert _normalize_threshold(0.55) == pytest.approx(0.55)


class TestComputeTotalSteps:
    def test_formula(self):
        assert compute_total_steps(n_combos=96, n_splits=5) == 5 * (96 + 1) + 2


class TestWalkForwardProgressCallback:
    @pytest.mark.asyncio
    async def test_on_progress_called_per_backtest(self):
        import numpy as np
        import pandas as pd

        n_combos = 2
        n_splits = 2
        expected_calls = compute_total_steps(n_combos, n_splits)
        progress_calls: list[tuple[int, int, str]] = []

        async def on_progress(completed: int, total: int, message: str) -> None:
            progress_calls.append((completed, total, message))

        df = pd.DataFrame({
            "time": pd.date_range("2020-01-01", periods=200, freq="D", tz="UTC"),
            "close": np.linspace(100, 150, 200),
        })

        with (
            patch(
                "features.quantitative_engine.mc_backtest_optimizer._run_backtest_metrics_async",
                new=AsyncMock(return_value=(1.0, -0.05)),
            ),
            patch(
                "features.quantitative_engine.mc_backtest_optimizer.run_mc_backtest",
                return_value=MagicMock(metrics={"sharpe_ratio": 1.0}),
            ),
            patch(
                "features.quantitative_engine.mc_backtest_optimizer.validate_param_grid",
                return_value=[{"buy_threshold": 0.55}, {"buy_threshold": 0.58}],
            ),
            patch(
                "features.quantitative_engine.mc_backtest_optimizer.split_timeseries",
                return_value=[
                    (df.iloc[:100], df.iloc[100:150]),
                    (df.iloc[:120], df.iloc[120:170]),
                ],
            ),
        ):
            await walk_forward_mc_backtest_optimize_async(
                df,
                param_grid={"buy_threshold": [55, 58]},
                n_splits=n_splits,
                timeframe="1d",
                model_type="merton",
                eval_start=datetime(2020, 6, 1, tzinfo=timezone.utc),
                eval_end=datetime(2020, 12, 1, tzinfo=timezone.utc),
                optimize_metric="sharpe_ratio",
                on_progress=on_progress,
            )

        assert len(progress_calls) == expected_calls
        assert progress_calls[-1][0] == expected_calls
        assert progress_calls[-1][1] == expected_calls
