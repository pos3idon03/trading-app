"""Tests for multi-timeframe MC context."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from features.quantitative_engine.mc_mtf import (
    build_mtf_context_series,
    mc_data_load_timeframe,
    mtf_allows_buy,
    MtfBarContext,
)


def _ohlcv(n: int = 200, freq: str = "h") -> pd.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    times = pd.date_range(start, periods=n, freq=freq, tz=timezone.utc)
    close = 100 + np.cumsum(np.random.default_rng(1).normal(0, 0.2, n))
    return pd.DataFrame({
        "time": times,
        "open": close,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": 1000.0,
    })


class TestMcDataLoadTimeframe:
    def test_finest_execution_and_regime(self):
        assert mc_data_load_timeframe("15m", "4h", None) == "15m"
        assert mc_data_load_timeframe("1d", "4h", "1h") == "1h"


class TestMtfAllowsBuy:
    def test_gate_off_always_allows(self):
        assert mtf_allows_buy(None, "merton", False, 0.3, False, 0.7) is True

    def test_blocks_low_trend_for_merton(self):
        ctx = MtfBarContext(regime_w_trend=0.1)
        assert mtf_allows_buy(ctx, "merton", True, 0.3, False, 0.7) is False

    def test_allows_high_trend_for_merton(self):
        ctx = MtfBarContext(regime_w_trend=0.5)
        assert mtf_allows_buy(ctx, "merton", True, 0.3, False, 0.7) is True

    def test_ou_blocks_high_trend_regime(self):
        ctx = MtfBarContext(regime_w_trend=0.8)
        assert mtf_allows_buy(ctx, "ou_deviation", True, 0.3, False, 0.7) is False


class TestBuildMtfContext:
    def test_regime_series_length_matches_eval(self):
        full = _ohlcv(300, "h")
        eval_df = full.iloc[-50:].reset_index(drop=True)
        ctx = build_mtf_context_series(full, eval_df, "4h", None, 14)
        assert len(ctx) == len(eval_df)
