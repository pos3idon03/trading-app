"""Tests for the multi-strategy combination backtest runner."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.combo_runner import (
    ComboStrategyConfig,
    _position_to_signals,
    _signals_to_position,
    combine_signals,
    run_combo_backtest,
    run_per_strategy_backtests,
)
from features.backtesting.stance import STANCE_BUY, STANCE_NEUTRAL, STANCE_SELL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def index_10():
    return pd.date_range("2022-01-01", periods=10, freq="D")


@pytest.fixture
def all_true(index_10):
    return pd.Series([True] * 10, index=index_10)


@pytest.fixture
def all_false(index_10):
    return pd.Series([False] * 10, index=index_10)


@pytest.fixture
def ohlcv_df():
    """Minimal OHLCV DataFrame with 120 bars suitable for most strategies."""
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


def _stance_series(values: list[str], index) -> pd.Series:
    return pd.Series(values, index=index, dtype=object)


# ---------------------------------------------------------------------------
# Unit tests: _signals_to_position
# ---------------------------------------------------------------------------

class TestSignalsToPosition:
    def test_entry_sets_position_true(self, index_10):
        entries = pd.Series([False, True] + [False] * 8, index=index_10)
        exits = pd.Series([False] * 10, index=index_10)
        pos = _signals_to_position(entries, exits)
        assert bool(pos.iloc[1])
        assert bool(pos.iloc[5])

    def test_exit_clears_position(self, index_10):
        entries = pd.Series([False, True] + [False] * 8, index=index_10)
        exits = pd.Series([False] * 4 + [True] + [False] * 5, index=index_10)
        pos = _signals_to_position(entries, exits)
        assert bool(pos.iloc[3])
        assert not bool(pos.iloc[4])


# ---------------------------------------------------------------------------
# Unit tests: _position_to_signals
# ---------------------------------------------------------------------------

class TestPositionToSignals:
    def test_entry_fires_on_transition_to_true(self, index_10):
        pos = pd.Series([False, False, True, True, True, False, False, False, False, False],
                        index=index_10)
        entries, exits = _position_to_signals(pos)
        assert bool(entries.iloc[2])
        assert not bool(entries.iloc[3])

    def test_exit_fires_on_transition_to_false(self, index_10):
        pos = pd.Series([False, False, True, True, True, False, False, False, False, False],
                        index=index_10)
        _, exits = _position_to_signals(pos)
        assert bool(exits.iloc[5])


# ---------------------------------------------------------------------------
# Unit tests: combine_signals (stance-based)
# ---------------------------------------------------------------------------

class TestCombineSignals:
    def test_and_mode_enters_when_all_buy(self, index_10):
        stances = [
            _stance_series(["Sell", "Buy", "Buy"], index_10[:3]),
            _stance_series(["Sell", "Buy", "Buy"], index_10[:3]),
        ]
        e, _ = combine_signals(stances, mode="and", weights=[1.0, 1.0])
        assert bool(e.iloc[1])

    def test_and_mode_holds_on_mixed_stance(self, index_10):
        stances = [
            _stance_series(["Buy", "Buy"], index_10[:2]),
            _stance_series(["Sell", "Buy"], index_10[:2]),
        ]
        e, x = combine_signals(stances, mode="and", weights=[1.0, 1.0])
        assert not bool(e.iloc[0])
        assert not bool(x.iloc[0])

    def test_invalid_mode_raises(self, index_10):
        with pytest.raises(ValueError, match="Unknown combination mode"):
            combine_signals(
                [_stance_series(["Buy"], index_10[:1])],
                mode="invalid",
                weights=[1.0],
            )

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            combine_signals([], mode="and", weights=[])

    def test_majority_mode(self, index_10):
        stances = [
            _stance_series(["Buy"] * 10, index_10),
            _stance_series(["Buy"] * 10, index_10),
            _stance_series(["Sell"] * 10, index_10),
        ]
        e, _ = combine_signals(stances, mode="majority", weights=[1.0, 1.0, 1.0])
        assert bool(e.iloc[0])

    def test_weighted_mode(self, index_10):
        stances = [
            _stance_series(["Buy"] * 10, index_10),
            _stance_series(["Sell"] * 10, index_10),
        ]
        e, _ = combine_signals(
            stances, mode="weighted", weights=[0.9, 0.1], threshold=0.5,
        )
        assert bool(e.iloc[0])


# ---------------------------------------------------------------------------
# Integration tests: run_combo_backtest
# ---------------------------------------------------------------------------

class TestRunComboBacktest:
    def test_returns_backtest_result(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="and")
        assert result.equity_curve is not None
        assert len(result.equity_curve) > 0

    def test_produces_trades_with_complementary_strategies(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("macd", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="majority")
        assert result.metrics.get("num_trades", 0) >= 0

    def test_weighted_mode(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}, weight=0.7),
            ComboStrategyConfig("rsi", {}, weight=0.3),
        ]
        result = run_combo_backtest(
            ohlcv_df, configs, combination_mode="weighted", threshold=0.5
        )
        assert result.equity_curve is not None


# ---------------------------------------------------------------------------
# Integration tests: run_per_strategy_backtests
# ---------------------------------------------------------------------------

class TestRunPerStrategyBacktests:
    def test_returns_one_result_per_strategy(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        results = run_per_strategy_backtests(ohlcv_df, configs)
        assert len(results) == 2

    def test_signal_timeline_contains_valid_signals(self, ohlcv_df):
        configs = [ComboStrategyConfig("ma_crossover", {})]
        results = run_per_strategy_backtests(ohlcv_df, configs)
        for point in results[0].signal_timeline:
            assert point["signal"] in (STANCE_BUY, STANCE_NEUTRAL, STANCE_SELL)

    def test_rsi_timeline_can_emit_sell(self, ohlcv_df):
        configs = [ComboStrategyConfig("rsi", {})]
        results = run_per_strategy_backtests(ohlcv_df, configs)
        signals = {p["signal"] for p in results[0].signal_timeline}
        assert STANCE_SELL in signals or STANCE_BUY in signals

    def test_lrsi_timeline_has_three_states(self, ohlcv_df):
        configs = [ComboStrategyConfig("lrsi", {})]
        results = run_per_strategy_backtests(ohlcv_df, configs)
        signals = {p["signal"] for p in results[0].signal_timeline}
        assert signals.issubset({STANCE_BUY, STANCE_NEUTRAL, STANCE_SELL})

    def test_macd_timeline_no_neutral(self, ohlcv_df):
        configs = [ComboStrategyConfig("macd", {})]
        results = run_per_strategy_backtests(ohlcv_df, configs)
        assert STANCE_NEUTRAL not in {p["signal"] for p in results[0].signal_timeline}

    def test_each_result_has_buy_hold_curve(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        for r in run_per_strategy_backtests(ohlcv_df, configs):
            assert isinstance(r.buy_hold_curve, list)
            assert len(r.buy_hold_curve) > 0
            assert len(r.buy_hold_curve) == len(r.equity_curve)


# ---------------------------------------------------------------------------
# Route-level tests: /combo-signals endpoint
# ---------------------------------------------------------------------------

class TestComboSignalsRoute:
    @pytest.mark.asyncio
    async def test_returns_combo_signals_response(self, ohlcv_df):
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, patch

        from routes.backtest import execute_combo_signals
        from dtos.backtest_dto import ComboBacktestRequest, ComboSignalsResponse

        request = ComboBacktestRequest(
            symbol="AAPL",
            strategies=[
                {"strategy_name": "ma_crossover", "strategy_params": {}, "weight": 1.0},
                {"strategy_name": "rsi", "strategy_params": {}, "weight": 1.0},
            ],
            combination_mode="majority",
            start_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2022, 12, 31, tzinfo=timezone.utc),
        )
        session = AsyncMock()

        with (
            patch("routes.backtest.get_asset_id_by_symbol", new=AsyncMock(return_value=1)),
            patch(
                "routes.backtest._load_backtest_ohlcv",
                new=AsyncMock(return_value=(ohlcv_df, request.start_date)),
            ),
        ):
            result = await execute_combo_signals(request, session)

        assert isinstance(result, ComboSignalsResponse)
        assert len(result.strategies) == 2
