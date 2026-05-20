"""Tests for MC backtest optimize background job routes."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from dtos.simulation_dto import McBacktestOptimizeRequest


def _make_df(rows: int = 200) -> pd.DataFrame:
    return pd.DataFrame({
        "time": pd.date_range("2020-01-01", periods=rows, freq="D", tz="UTC"),
        "close": np.linspace(100, 150, rows),
    })


class TestOptimizeMcBacktestJobRoute:
    @pytest.mark.asyncio
    async def test_post_returns_202_with_job_id(self):
        from routes.monte_carlo import optimize_mc_backtest

        session = AsyncMock()
        request = McBacktestOptimizeRequest(
            symbol="AAPL",
            start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            param_grid={
                "buy_threshold": [55],
                "sell_threshold": [48],
                "num_paths": [500],
            },
            n_splits=2,
        )

        with (
            patch("routes.monte_carlo._resolve_asset_id", new=AsyncMock(return_value=1)),
            patch("routes.monte_carlo.get_ohlcv", new=AsyncMock(return_value=_make_df())),
            patch("routes.monte_carlo.create_job", new=AsyncMock(return_value=42)),
            patch("routes.monte_carlo.asyncio.create_task") as mock_task,
        ):
            resp = await optimize_mc_backtest(request, session)

        assert resp.job_id == 42
        assert resp.status == "pending"
        mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_returns_progress(self):
        from routes.monte_carlo import get_mc_backtest_optimize_job

        session = AsyncMock()
        job = MagicMock()
        job.id = 42
        job.asset_id = 1
        job.symbol = "AAPL"
        job.status = "running"
        job.progress_pct = 25.0
        job.progress_message = "Fold 1/5"
        job.completed_steps = 120
        job.total_steps = 481
        job.duration_ms = None
        job.error_message = None
        job.result = None
        job.request = {
            "optimize_metric": "sharpe_ratio",
            "n_splits": 5,
        }

        with patch("routes.monte_carlo.get_job", new=AsyncMock(return_value=job)):
            resp = await get_mc_backtest_optimize_job(42, session)

        assert resp.job_id == 42
        assert resp.status == "running"
        assert resp.progress_pct == pytest.approx(25.0)
        assert resp.progress_message == "Fold 1/5"
        assert resp.completed_steps == 120

    @pytest.mark.asyncio
    async def test_get_job_not_found_404(self):
        from routes.monte_carlo import get_mc_backtest_optimize_job

        session = AsyncMock()
        with patch("routes.monte_carlo.get_job", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc_info:
                await get_mc_backtest_optimize_job(999, session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_done_includes_result(self):
        from routes.monte_carlo import get_mc_backtest_optimize_job

        session = AsyncMock()
        job = MagicMock()
        job.id = 7
        job.asset_id = 1
        job.symbol = "AAPL"
        job.status = "done"
        job.progress_pct = 100.0
        job.progress_message = "Complete"
        job.completed_steps = 10
        job.total_steps = 10
        job.duration_ms = 500
        job.error_message = None
        job.request = {"optimize_metric": "sharpe_ratio", "n_splits": 2}
        job.result = {
            "best_params": {"buy_threshold": 0.55},
            "best_metric": 1.1,
            "best_avg_oos_max_drawdown": -0.1,
            "all_results": [{
                "params": {"buy_threshold": 0.55},
                "avg_oos_metric": 1.1,
                "avg_oos_max_drawdown": -0.1,
            }],
            "full_period_metrics": {
                "total_return": 0.1,
                "sharpe_ratio": 1.0,
                "sortino_ratio": 1.1,
                "max_drawdown": -0.05,
                "win_rate": 0.5,
                "profit_factor": 1.2,
                "num_trades": 3,
            },
            "duration_ms": 500,
        }

        with patch("routes.monte_carlo.get_job", new=AsyncMock(return_value=job)):
            resp = await get_mc_backtest_optimize_job(7, session)

        assert resp.status == "done"
        assert resp.best_params == {"buy_threshold": 0.55}
        assert resp.best_metric == pytest.approx(1.1)
        assert resp.full_period_metrics is not None
        assert resp.full_period_metrics.sharpe_ratio == pytest.approx(1.0)
