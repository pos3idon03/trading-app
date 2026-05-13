"""Unit tests for compute_strategy_signals."""
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from features.live_trading.strategy_signals import (
    MIN_BARS_REQUIRED,
    _build_dataframe,
    _determine_signal,
    _run_single_strategy,
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
    """Create n synthetic OHLCV bars with slight upward drift."""
    bars = []
    for i in range(n):
        close = 100.0 + i * 0.1
        bars.append(_make_bar(close=close, open_=close - 0.5, high=close + 0.5, low=close - 1.0))
    return bars


class TestBuildDataframe:
    def test_converts_bars_to_dataframe(self):
        bars = _make_bars(5)
        df = _build_dataframe(bars)
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert len(df) == 5

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
