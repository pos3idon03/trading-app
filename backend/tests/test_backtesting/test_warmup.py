"""Tests for indicator warm-up helpers."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from features.backtesting.runner import run_backtest
from features.backtesting.warmup import (
    count_evaluation_rows,
    evaluation_mask,
    max_warmup_bars,
    required_warmup_bars,
    slice_df_segment,
    slice_time_series_rows,
    warmup_start_datetime,
)


class TestRequiredWarmupBars:
    def test_sma_cross_slow_window(self):
        assert required_warmup_bars("sma_cross", {"slow_window": 200}) >= 200

    def test_ma_cross_defaults(self):
        bars = required_warmup_bars("ma_crossover", {})
        assert bars >= 50

    def test_seasonal_no_warmup(self):
        assert required_warmup_bars("seasonal", {}) == 5

    def test_combo_max(self):
        legs = [
            ("sma_cross", {"slow_window": 200}),
            ("rsi", {"period": 14}),
        ]
        assert max_warmup_bars(legs) >= 200


class TestWarmupStartDatetime:
    def test_daily_moves_backward(self):
        start = datetime(2023, 5, 15, tzinfo=timezone.utc)
        earlier = warmup_start_datetime(start, 200, "1d")
        assert earlier < start
        assert (start - earlier).days >= 200


class TestEvaluationWindow:
    @pytest.fixture
    def extended_df(self):
        n_warmup = 250
        n_eval = 30
        dates = pd.date_range("2020-01-01", periods=n_warmup + n_eval, freq="D")
        close = np.linspace(100, 130, len(dates))
        return pd.DataFrame({
            "time": dates,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000.0,
        })

    def test_evaluation_mask(self, extended_df):
        eval_start = pd.Timestamp(extended_df.iloc[250]["time"]).to_pydatetime()
        mask = evaluation_mask(extended_df, eval_start)
        assert mask.sum() == 30

    def test_sma_cross_indicator_valid_on_first_eval_bar(self, extended_df):
        eval_start = pd.Timestamp(extended_df.iloc[250]["time"])
        result = run_backtest(
            extended_df,
            strategy="sma_cross",
            params={"fast_window": 50, "slow_window": 200},
            evaluation_start=eval_start.to_pydatetime(),
        )
        assert len(result.indicator_series) == 30
        first = result.indicator_series[0]
        assert first["slow_sma"] is not None

    def test_slice_df_segment_includes_warmup_rows(self, extended_df):
        seg_start = datetime(2020, 9, 6, tzinfo=timezone.utc)
        seg_end = datetime(2020, 9, 15, tzinfo=timezone.utc)
        chunk, eval_start = slice_df_segment(extended_df, seg_start, seg_end, 200)
        assert len(chunk) > 10
        assert eval_start == seg_start
        assert count_evaluation_rows(chunk, eval_start) == 10

    def test_slice_time_series_rows(self):
        rows = [
            {"time": "2020-01-01", "v": 1},
            {"time": "2020-09-06", "v": 2},
        ]
        out = slice_time_series_rows(rows, datetime(2020, 9, 1, tzinfo=timezone.utc))
        assert len(out) == 1
        assert out[0]["time"] == "2020-09-06"
