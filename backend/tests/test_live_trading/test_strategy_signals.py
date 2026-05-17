"""Unit tests for compute_strategy_signals."""
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from features.live_trading.strategy_signals import (
    MIN_BARS_REQUIRED,
    _build_dataframe,
    _build_signal_timeline,
    _compute_key_indicator,
    _determine_signal,
    _determine_signal_at_index,
    _run_single_strategy,
    _run_strategy_full,
    compute_strategy_signals,
)


def _make_bar(close: float = 100.0, open_: float = 99.0, high: float = 101.0, low: float = 98.0, volume: int = 1000):
    bar = MagicMock()
    bar.open = open_
    bar.high = high
    bar.low = low
    bar.close = close
    bar.volume = volume
    return bar


def _make_bars(n: int = 50) -> list:
    """Create n synthetic OHLCV bars with realistic oscillating prices (not purely monotonic)."""
    import math
    bars = []
    for i in range(n):
        # Sine wave so price oscillates up and down, enabling proper indicator calculation
        close = 100.0 + 5.0 * math.sin(i * 0.3) + i * 0.05
        bars.append(_make_bar(close=close, open_=close - 0.5, high=close + 1.0, low=close - 1.0))
    return bars


class TestBuildDataframe:
    def test_converts_bars_to_dataframe(self):
        bars = _make_bars(5)
        df = _build_dataframe(bars)
        assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
        assert len(df) == 5

    def test_includes_bar_start_timestamp(self):
        from datetime import datetime, timezone
        bar = _make_bar()
        bar.bar_start = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
        df = _build_dataframe([bar])
        assert "2026-05-14" in df["time"].iloc[0]

    def test_columns_are_lowercase(self):
        bars = _make_bars(3)
        df = _build_dataframe(bars)
        for col in df.columns:
            assert col == col.lower()


class TestDetermineSignal:
    def test_buy_when_last_entry_true(self):
        entries = pd.Series([False, False, True])
        exits = pd.Series([False, False, False])
        assert _determine_signal(entries, exits) == "BUY"

    def test_sell_when_last_exit_true_and_no_entry(self):
        entries = pd.Series([False, False, False])
        exits = pd.Series([False, False, True])
        assert _determine_signal(entries, exits) == "SELL"

    def test_buy_takes_priority_over_sell(self):
        entries = pd.Series([False, False, True])
        exits = pd.Series([False, False, True])
        assert _determine_signal(entries, exits) == "BUY"

    def test_neutral_when_both_false(self):
        entries = pd.Series([False, False, False])
        exits = pd.Series([False, False, False])
        assert _determine_signal(entries, exits) == "NEUTRAL"

    def test_neutral_on_empty_series(self):
        assert _determine_signal(pd.Series([], dtype=bool), pd.Series([], dtype=bool)) == "NEUTRAL"


class TestRunSingleStrategy:
    def test_returns_valid_signal_string(self):
        bars = _make_bars(60)
        df = _build_dataframe(bars)
        result = _run_single_strategy("rsi", df)
        assert result in ("BUY", "SELL", "NEUTRAL")

    def test_unknown_strategy_returns_neutral(self):
        df = _build_dataframe(_make_bars(5))
        result = _run_single_strategy("nonexistent_strategy", df)
        assert result == "NEUTRAL"

    def test_strategy_exception_returns_neutral(self):
        df = _build_dataframe(_make_bars(5))
        with patch("features.live_trading.strategy_signals._STRATEGY_MAP", {"bad": MagicMock(side_effect=RuntimeError("boom"))}):
            result = _run_single_strategy("bad", df)
        assert result == "NEUTRAL"


class TestComputeKeyIndicator:
    def test_rsi_returns_float_value(self):
        df = _build_dataframe(_make_bars(60))
        value, label = _compute_key_indicator("rsi", df, {"period": 14})
        assert label == "RSI"
        assert value is not None
        assert 0.0 <= value <= 100.0

    def test_macd_returns_histogram_value(self):
        df = _build_dataframe(_make_bars(60))
        value, label = _compute_key_indicator("macd", df, {"fast": 12, "slow": 26, "signal": 9})
        assert label == "MACD Hist"
        assert isinstance(value, float)

    def test_unknown_strategy_returns_none(self):
        df = _build_dataframe(_make_bars(60))
        value, label = _compute_key_indicator("unknown_xyz", df, {})
        assert value is None
        assert label is None

    def test_lrsi_returns_value_between_zero_and_one(self):
        df = _build_dataframe(_make_bars(60))
        value, label = _compute_key_indicator("lrsi", df, {"gamma": 0.5})
        assert label == "LRSI"
        if value is not None:
            assert 0.0 <= value <= 1.0


class TestDetermineSignalAtIndex:
    def test_buy_at_index_when_entry_true(self):
        entries = pd.Series([False, True, False])
        exits = pd.Series([False, False, True])
        assert _determine_signal_at_index(entries, exits, 1) == "BUY"

    def test_sell_at_index_when_exit_true(self):
        entries = pd.Series([False, False, False])
        exits = pd.Series([False, False, True])
        assert _determine_signal_at_index(entries, exits, 2) == "SELL"


class TestBuildSignalTimeline:
    def test_returns_sliced_timeline_with_chart_signals(self):
        df = _build_dataframe(_make_bars(60))
        entries = pd.Series([False] * 59 + [True])
        exits = pd.Series([False] * 60)
        timeline = _build_signal_timeline(df, entries, exits, timeline_bars=10)
        assert len(timeline) == 10
        assert timeline[-1]["signal"] == "Buy"
        assert "time" in timeline[0]


class TestRunStrategyFull:
    def test_returns_five_tuple(self):
        df = _build_dataframe(_make_bars(60))
        result = _run_strategy_full("rsi", df)
        assert len(result) == 5
        signal, ind_val, ind_label, params, timeline = result
        assert signal in ("BUY", "SELL", "NEUTRAL")
        assert ind_label == "RSI"
        assert "period" in params
        assert timeline == []

    def test_include_timeline_populates_points(self):
        df = _build_dataframe(_make_bars(60))
        _, _, _, _, timeline = _run_strategy_full(
            "rsi", df, include_timeline=True, timeline_bars=20,
        )
        assert len(timeline) == 20
        assert timeline[-1]["signal"] in ("Buy", "Sell", "Neutral")

    def test_unknown_strategy_returns_neutral_with_no_indicator(self):
        df = _build_dataframe(_make_bars(10))
        signal, ind_val, ind_label, params, timeline = _run_strategy_full("nonexistent", df)
        assert signal == "NEUTRAL"
        assert ind_val is None
        assert ind_label is None
        assert timeline == []


class TestComputeStrategySignals:
    def test_returns_empty_list_when_insufficient_bars(self):
        bars = _make_bars(MIN_BARS_REQUIRED - 1)
        result = compute_strategy_signals(bars, "AAPL")
        assert result == []

    def test_returns_results_for_all_strategies(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        assert len(results) > 0

    def test_each_result_has_valid_signal(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        for r in results:
            assert r.signal in ("BUY", "SELL", "NEUTRAL")

    def test_each_result_has_label_and_group(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        for r in results:
            assert r.label
            assert r.group

    def test_strategy_names_are_unique(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        names = [r.strategy for r in results]
        assert len(names) == len(set(names))

    def test_minimum_bar_boundary(self):
        bars = _make_bars(MIN_BARS_REQUIRED)
        result = compute_strategy_signals(bars, "MSFT")
        assert isinstance(result, list)

    def test_results_include_indicator_value_and_params(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        rsi_result = next((r for r in results if r.strategy == "rsi"), None)
        assert rsi_result is not None
        assert rsi_result.indicator_value is not None
        assert rsi_result.indicator_label == "RSI"
        assert isinstance(rsi_result.params, dict)
        assert "period" in rsi_result.params

    def test_params_dict_is_not_none_for_all_strategies(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        for r in results:
            assert isinstance(r.params, dict)

    def test_include_timeline_adds_signal_timeline(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(
            bars, "AAPL", include_timeline=True, timeline_bars=30,
        )
        rsi = next(r for r in results if r.strategy == "rsi")
        assert len(rsi.signal_timeline) == 30
        assert rsi.signal_timeline[-1]["signal"] in ("Buy", "Sell", "Neutral")

    def test_without_timeline_flag_timeline_empty(self):
        bars = _make_bars(60)
        results = compute_strategy_signals(bars, "AAPL")
        for r in results:
            assert r.signal_timeline == []
