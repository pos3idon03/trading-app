"""Tests for the multi-strategy combination backtest runner."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.combo_runner import (
    ComboStrategyConfig,
    _combine_positions_and,
    _combine_positions_majority,
    _combine_positions_weighted,
    _position_to_signals,
    _signals_to_position,
    combine_signals,
    run_combo_backtest,
)


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


# ---------------------------------------------------------------------------
# Unit tests: _signals_to_position
# ---------------------------------------------------------------------------

class TestSignalsToPosition:
    def test_entry_sets_position_true(self, index_10):
        entries = pd.Series([False, True] + [False] * 8, index=index_10)
        exits = pd.Series([False] * 10, index=index_10)
        pos = _signals_to_position(entries, exits)
        assert pos.iloc[1] is True or pos.iloc[1]  # entered on bar 1
        assert pos.iloc[5] is True or pos.iloc[5]  # still in position

    def test_exit_clears_position(self, index_10):
        entries = pd.Series([False, True] + [False] * 8, index=index_10)
        exits = pd.Series([False] * 4 + [True] + [False] * 5, index=index_10)
        pos = _signals_to_position(entries, exits)
        assert bool(pos.iloc[3])   # in position before exit
        assert not bool(pos.iloc[4])  # out after exit on bar 4
        assert not bool(pos.iloc[7])  # still out

    def test_no_signals_all_false(self, all_false, index_10):
        pos = _signals_to_position(all_false, all_false)
        assert not pos.any()

    def test_returns_bool_series(self, all_true, all_false):
        pos = _signals_to_position(all_true, all_false)
        assert pos.dtype == bool or pos.dtype == object


# ---------------------------------------------------------------------------
# Unit tests: _position_to_signals
# ---------------------------------------------------------------------------

class TestPositionToSignals:
    def test_entry_fires_on_transition_to_true(self, index_10):
        pos = pd.Series([False, False, True, True, True, False, False, False, False, False],
                        index=index_10)
        entries, exits = _position_to_signals(pos)
        assert bool(entries.iloc[2])   # transition False→True
        assert not bool(entries.iloc[3])  # already in position

    def test_exit_fires_on_transition_to_false(self, index_10):
        pos = pd.Series([False, False, True, True, True, False, False, False, False, False],
                        index=index_10)
        entries, exits = _position_to_signals(pos)
        assert bool(exits.iloc[5])       # transition True→False
        assert not bool(exits.iloc[6])   # already out

    def test_roundtrip_preserves_position(self, index_10):
        pos = pd.Series([False, True, True, True, False, True, True, False, False, True],
                        index=index_10)
        entries, exits = _position_to_signals(pos)
        recovered = pd.Series(False, index=index_10)
        in_pos = False
        for i in range(len(index_10)):
            if entries.iloc[i]:
                in_pos = True
            if exits.iloc[i]:
                in_pos = False
            recovered.iloc[i] = in_pos
        # Recovered position should match original (first bar may differ due to no prior state)
        pd.testing.assert_series_equal(recovered.iloc[1:], pos.iloc[1:], check_names=False)


# ---------------------------------------------------------------------------
# Unit tests: _combine_positions_and
# ---------------------------------------------------------------------------

class TestCombinePositionsAnd:
    def test_both_in_position_yields_true(self, all_true, index_10):
        result = _combine_positions_and([all_true, all_true])
        assert result.all()

    def test_one_out_blocks_combined(self, all_true, all_false):
        result = _combine_positions_and([all_true, all_false])
        assert not result.any()

    def test_three_strategies_requires_all(self, all_true, all_false, index_10):
        result = _combine_positions_and([all_true, all_true, all_false])
        assert not result.any()


# ---------------------------------------------------------------------------
# Unit tests: _combine_positions_majority
# ---------------------------------------------------------------------------

class TestCombinePositionsMajority:
    def test_two_out_of_three_true(self, all_true, all_false):
        result = _combine_positions_majority([all_true, all_true, all_false])
        assert result.all()

    def test_one_out_of_three_false(self, all_true, all_false):
        result = _combine_positions_majority([all_true, all_false, all_false])
        assert not result.any()

    def test_exactly_half_not_majority(self, all_true, all_false):
        result = _combine_positions_majority([all_true, all_false])
        assert not result.any()


# ---------------------------------------------------------------------------
# Unit tests: _combine_positions_weighted
# ---------------------------------------------------------------------------

class TestCombinePositionsWeighted:
    def test_heavy_weight_dominates(self, all_true, all_false):
        result = _combine_positions_weighted([all_true, all_false], [0.9, 0.1], threshold=0.5)
        assert result.all()

    def test_below_threshold_no_signal(self, all_true, all_false):
        result = _combine_positions_weighted([all_true, all_false], [0.4, 0.6], threshold=0.5)
        assert not result.any()

    def test_zero_total_weight_raises(self, all_true, all_false):
        with pytest.raises(ValueError, match="Sum of weights must be > 0"):
            _combine_positions_weighted([all_true], [0.0], threshold=0.5)


# ---------------------------------------------------------------------------
# Unit tests: combine_signals (public API)
# ---------------------------------------------------------------------------

class TestCombineSignals:
    def test_and_mode_fires_when_both_in_position(self, index_10):
        """Entry A on bar 1, entry B on bar 4 → combined entry on bar 4."""
        entries_a = pd.Series([False, True] + [False] * 8, index=index_10)
        exits_a = pd.Series([False] * 10, index=index_10)
        entries_b = pd.Series([False] * 4 + [True] + [False] * 5, index=index_10)
        exits_b = pd.Series([False] * 10, index=index_10)
        e, x = combine_signals(
            [(entries_a, exits_a), (entries_b, exits_b)],
            mode="and", weights=[1.0, 1.0],
        )
        # Combined entry should fire on bar 4 (when B joins A already in position)
        assert bool(e.iloc[4])

    def test_and_mode_exits_when_either_exits(self, index_10):
        """Both in position from bar 1; A exits on bar 5 → combined exits on bar 5."""
        entries_a = pd.Series([False, True] + [False] * 8, index=index_10)
        exits_a = pd.Series([False] * 5 + [True] + [False] * 4, index=index_10)
        entries_b = pd.Series([False, True] + [False] * 8, index=index_10)
        exits_b = pd.Series([False] * 10, index=index_10)
        e, x = combine_signals(
            [(entries_a, exits_a), (entries_b, exits_b)],
            mode="and", weights=[1.0, 1.0],
        )
        assert bool(x.iloc[5])

    def test_invalid_mode_raises(self, all_true, all_false):
        with pytest.raises(ValueError, match="Unknown combination mode"):
            combine_signals([(all_true, all_false)], mode="invalid", weights=[1.0])

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            combine_signals([], mode="and", weights=[])

    def test_majority_mode(self, index_10):
        """2 out of 3 strategies in position → combined in position."""
        entries_a = pd.Series([False, True] + [False] * 8, index=index_10)
        entries_b = pd.Series([False, True] + [False] * 8, index=index_10)
        entries_c = pd.Series([False] * 10, index=index_10)
        no_exits = pd.Series([False] * 10, index=index_10)
        e, x = combine_signals(
            [(entries_a, no_exits), (entries_b, no_exits), (entries_c, no_exits)],
            mode="majority", weights=[1.0, 1.0, 1.0],
        )
        assert bool(e.iloc[1])  # 2/3 in position from bar 1

    def test_weighted_mode(self, index_10):
        entries_a = pd.Series([False, True] + [False] * 8, index=index_10)
        no_exits = pd.Series([False] * 10, index=index_10)
        entries_b = pd.Series([False] * 10, index=index_10)
        e, x = combine_signals(
            [(entries_a, no_exits), (entries_b, no_exits)],
            mode="weighted", weights=[0.9, 0.1], threshold=0.5,
        )
        assert bool(e.iloc[1])  # A (weight 0.9) enters; 0.9/1.0 > 0.5


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
        """Using majority mode with trending + momentum should yield trades."""
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("macd", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="majority")
        assert result.metrics.get("num_trades", 0) > 0

    def test_equity_curve_has_time_and_value(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("macd", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="majority")
        for point in result.equity_curve:
            assert "time" in point
            assert "value" in point

    def test_buy_hold_curve_present(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="and")
        assert result.buy_hold_curve is not None
        assert len(result.buy_hold_curve) > 0

    def test_metrics_populated(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="majority")
        assert "sharpe_ratio" in result.metrics

    def test_weighted_mode(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}, weight=0.7),
            ComboStrategyConfig("rsi", {}, weight=0.3),
        ]
        result = run_combo_backtest(
            ohlcv_df, configs, combination_mode="weighted", threshold=0.5
        )
        assert result.equity_curve is not None

    def test_duration_ms_positive(self, ohlcv_df):
        configs = [
            ComboStrategyConfig("ma_crossover", {}),
            ComboStrategyConfig("rsi", {}),
        ]
        result = run_combo_backtest(ohlcv_df, configs, combination_mode="and")
        assert result.duration_ms > 0
