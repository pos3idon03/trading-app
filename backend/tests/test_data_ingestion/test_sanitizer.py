"""Tests for the OHLCV sanitization pipeline."""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta

from features.data_ingestion.sanitizer import (
    detect_gaps,
    forward_fill_gaps,
    validate_ohlcv,
    adjust_splits_dividends,
    run_sanitization_pipeline,
)


def make_df(n: int = 10, timeframe: str = "1d") -> pd.DataFrame:
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    step = timedelta(days=1)
    times = [base + i * step for i in range(n)]
    prices = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame({
        "time": times,
        "open": prices - 0.5,
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices,
        "volume": [1_000_000] * n,
        "source": ["test"] * n,
    })


class TestValidateOHLCV:
    def test_valid_df_passes(self):
        df = make_df()
        result = validate_ohlcv(df)
        assert result.is_valid

    def test_missing_column_fails(self):
        df = make_df().drop(columns=["volume"])
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("volume" in e for e in result.errors)

    def test_high_less_than_low_fails(self):
        df = make_df()
        df.loc[3, "high"] = df.loc[3, "low"] - 1
        result = validate_ohlcv(df)
        assert not result.is_valid

    def test_negative_volume_fails(self):
        df = make_df()
        df.loc[0, "volume"] = -100
        result = validate_ohlcv(df)
        assert not result.is_valid

    def test_empty_df_returns_warning(self):
        result = validate_ohlcv(pd.DataFrame())
        assert result.is_valid
        assert result.warnings


class TestDetectGaps:
    def test_no_gaps(self):
        df = make_df(10)
        gaps = detect_gaps(df, "1d")
        assert gaps.empty

    def test_detects_single_gap(self):
        df = make_df(10)
        df = df.drop(index=5).reset_index(drop=True)
        gaps = detect_gaps(df, "1d")
        assert not gaps.empty
        assert gaps.iloc[0]["missing_bars"] == 1

    def test_large_gap_detected(self):
        df = make_df(10)
        df = df[df.index != 3].reset_index(drop=True)
        df = df[df.index != 3].reset_index(drop=True)
        gaps = detect_gaps(df, "1d")
        assert not gaps.empty


class TestForwardFillGaps:
    def test_fills_single_missing_bar(self):
        df = make_df(10)
        df_with_gap = df.drop(index=5).reset_index(drop=True)
        filled = forward_fill_gaps(df_with_gap, "1d")
        assert len(filled) == len(df)
        filled_rows = filled[filled["filled"] == True]
        assert len(filled_rows) == 1

    def test_no_fill_for_large_gap(self):
        df = make_df(20)
        indices_to_drop = list(range(5, 15))
        df_gapped = df.drop(index=indices_to_drop).reset_index(drop=True)
        filled = forward_fill_gaps(df_gapped, "1d")
        assert "filled" in filled.columns


class TestAdjustSplitsAndDividends:
    def test_split_halves_pre_event_prices(self):
        df = make_df(10)
        event_date = df["time"].iloc[5]
        events = [{"date": event_date, "split_ratio": 2.0, "dividend": 0.0}]
        adjusted = adjust_splits_dividends(df.copy(), events)
        assert adjusted.loc[0, "close"] < df.loc[0, "close"]

    def test_no_events_returns_unchanged(self):
        df = make_df(10)
        adjusted = adjust_splits_dividends(df.copy(), [])
        pd.testing.assert_frame_equal(df, adjusted)


class TestRunSanitizationPipeline:
    def test_pipeline_runs_on_clean_data(self, sample_ohlcv_df):
        result = run_sanitization_pipeline(sample_ohlcv_df, "1d")
        assert not result.empty
        assert "close" in result.columns

    def test_pipeline_raises_on_invalid_data(self):
        df = make_df(5)
        df.loc[0, "high"] = df.loc[0, "low"] - 1
        with pytest.raises(ValueError):
            run_sanitization_pipeline(df, "1d")
