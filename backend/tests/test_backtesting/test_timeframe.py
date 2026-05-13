"""Tests for Daily/Weekly timeframe support in backtest DTO, runner, and route helpers."""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

from dtos.backtest_dto import BacktestRequest, OptimizationRequest
from features.backtesting.runner import _TIMEFRAME_TO_VBT_FREQ, run_backtest
from routes.backtest import _ohlcv_query_args


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n: int = 100, freq: str = "D") -> pd.DataFrame:
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.01, n)
    close = pd.Series(50.0 * np.cumprod(1 + returns))
    dates = pd.date_range("2020-01-01", periods=n, freq=freq)
    return pd.DataFrame({
        "time": dates,
        "open": close.values,
        "high": close.values * 1.005,
        "low": close.values * 0.995,
        "close": close.values,
        "volume": 1_000.0,
    })


# ---------------------------------------------------------------------------
# DTO validation — timeframe field
# ---------------------------------------------------------------------------

class TestBacktestRequestTimeframeValidation:
    def _base(self) -> dict:
        return {
            "symbol": "AAPL",
            "strategy_name": "ma_crossover",
            "start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        }

    def test_default_timeframe_is_daily(self):
        req = BacktestRequest(**self._base())
        assert req.timeframe == "1d"

    def test_accepts_daily_timeframe(self):
        req = BacktestRequest(timeframe="1d", **self._base())
        assert req.timeframe == "1d"

    def test_accepts_weekly_timeframe(self):
        req = BacktestRequest(timeframe="1w", **self._base())
        assert req.timeframe == "1w"

    def test_rejects_invalid_timeframe(self):
        with pytest.raises(ValidationError):
            BacktestRequest(timeframe="4h", **self._base())

    def test_rejects_raw_string_timeframe(self):
        with pytest.raises(ValidationError):
            BacktestRequest(timeframe="daily", **self._base())


class TestOptimizationRequestTimeframeValidation:
    def _base(self) -> dict:
        return {
            "symbol": "AAPL",
            "strategy_name": "ma_crossover",
            "start_date": datetime(2022, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
            "param_grid": {"fast_window": [5, 10]},
        }

    def test_accepts_weekly_timeframe(self):
        req = OptimizationRequest(timeframe="1w", **self._base())
        assert req.timeframe == "1w"

    def test_rejects_invalid_timeframe(self):
        with pytest.raises(ValidationError):
            OptimizationRequest(timeframe="1h", **self._base())


# ---------------------------------------------------------------------------
# _TIMEFRAME_TO_VBT_FREQ mapping
# ---------------------------------------------------------------------------

class TestTimeframeToVbtFreq:
    def test_daily_maps_to_D(self):
        assert _TIMEFRAME_TO_VBT_FREQ["1d"] == "D"

    def test_weekly_maps_to_W(self):
        assert _TIMEFRAME_TO_VBT_FREQ["1w"] == "W"


# ---------------------------------------------------------------------------
# run_backtest — timeframe parameter wires the correct vectorbt freq
# ---------------------------------------------------------------------------

class TestRunBacktestTimeframe:
    def test_daily_backtest_completes(self):
        df = _make_ohlcv_df(n=100, freq="D")
        result = run_backtest(df, strategy="ma_crossover", params={}, timeframe="1d")
        assert result.metrics is not None
        assert result.equity_curve is not None

    def test_weekly_backtest_completes(self):
        df = _make_ohlcv_df(n=104, freq="W")
        result = run_backtest(df, strategy="ma_crossover", params={}, timeframe="1w")
        assert result.metrics is not None
        assert result.equity_curve is not None

    def test_default_timeframe_behaves_as_daily(self):
        df = _make_ohlcv_df(n=100, freq="D")
        result_default = run_backtest(df, strategy="ma_crossover", params={})
        result_daily = run_backtest(df, strategy="ma_crossover", params={}, timeframe="1d")
        assert result_default.metrics["sharpe_ratio"] == pytest.approx(
            result_daily.metrics["sharpe_ratio"], abs=1e-6
        )

    def test_unknown_timeframe_falls_back_to_daily(self):
        df = _make_ohlcv_df(n=100, freq="D")
        result = run_backtest(df, strategy="ma_crossover", params={}, timeframe="unknown")
        assert result.metrics is not None


# ---------------------------------------------------------------------------
# _ohlcv_query_args helper
# ---------------------------------------------------------------------------

class TestOhlcvQueryArgs:
    def test_daily_returns_direct_timeframe(self):
        args = _ohlcv_query_args("1d")
        assert args == {"timeframe": "1d"}
        assert "bucket_interval" not in args

    def test_weekly_returns_daily_source_with_bucket(self):
        args = _ohlcv_query_args("1w")
        assert args["timeframe"] == "1d"
        assert args["bucket_interval"] == timedelta(weeks=1)

    def test_daily_does_not_include_bucket_interval(self):
        args = _ohlcv_query_args("1d")
        assert "bucket_interval" not in args
