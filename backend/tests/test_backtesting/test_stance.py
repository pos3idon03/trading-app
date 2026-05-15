"""Tests for per-bar Buy / Neutral / Sell stance computation and combination."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.stance import (
    STANCE_BUY,
    STANCE_NEUTRAL,
    STANCE_SELL,
    _decide_bar_target,
    _zone_stance,
    combine_stances,
    compute_strategy_stance,
)


@pytest.fixture
def index_10():
    return pd.date_range("2022-01-01", periods=10, freq="D")


@pytest.fixture
def ohlcv_df(index_10):
    n = len(index_10)
    close = np.linspace(100, 110, n)
    return pd.DataFrame({
        "time": index_10,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": 1000.0,
    })


class TestZoneStance:
    def test_below_oversold_is_buy(self):
        values = pd.Series([0.1, 0.5, 0.9])
        stance = _zone_stance(values, 0.2, 0.8)
        assert stance.iloc[0] == STANCE_BUY
        assert stance.iloc[1] == STANCE_NEUTRAL
        assert stance.iloc[2] == STANCE_SELL

    def test_on_threshold_is_neutral(self):
        values = pd.Series([0.2, 0.8])
        stance = _zone_stance(values, 0.2, 0.8)
        assert stance.iloc[0] == STANCE_NEUTRAL
        assert stance.iloc[1] == STANCE_NEUTRAL


class TestDecideBarTarget:
    def test_and_all_buy(self):
        assert _decide_bar_target(["Buy", "Buy"], "and", [1.0, 1.0], 0.5) == "long"

    def test_and_all_sell(self):
        assert _decide_bar_target(["Sell", "Sell"], "and", [1.0, 1.0], 0.5) == "flat"

    def test_and_mixed_holds(self):
        assert _decide_bar_target(["Buy", "Sell"], "and", [1.0, 1.0], 0.5) is None
        assert _decide_bar_target(["Buy", "Neutral"], "and", [1.0, 1.0], 0.5) is None

    def test_majority_buy_wins(self):
        assert _decide_bar_target(["Buy", "Buy", "Sell"], "majority", [1, 1, 1], 0.5) == "long"

    def test_majority_tie_holds(self):
        assert _decide_bar_target(["Buy", "Sell"], "majority", [1, 1], 0.5) is None

    def test_majority_neutral_abstains(self):
        assert _decide_bar_target(["Buy", "Neutral"], "majority", [1, 1], 0.5) == "long"

    def test_weighted_hold_band(self):
        assert _decide_bar_target(["Buy", "Sell"], "weighted", [0.5, 0.5], 0.6) is None


class TestCombineStances:
    def test_hysteresis_on_and_mode(self, index_10):
        a = pd.Series(["Buy"] * 10, index=index_10)
        b = pd.Series(["Sell"] * 10, index=index_10)
        pos = combine_stances([a, b], "and", [1.0, 1.0])
        assert not pos.any()

    def test_and_enters_when_all_buy(self, index_10):
        a = pd.Series(["Sell", "Buy", "Buy"], index=index_10[:3])
        b = pd.Series(["Sell", "Buy", "Buy"], index=index_10[:3])
        pos = combine_stances([a, b], "and", [1.0, 1.0])
        assert not pos.iloc[0]
        assert pos.iloc[1]
        assert pos.iloc[2]

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            combine_stances([], "and", [])


class TestComputeStrategyStance:
    def test_lrsi_has_three_states(self, ohlcv_df):
        stance = compute_strategy_stance(ohlcv_df, "lrsi", {})
        assert set(stance.unique()).issubset({STANCE_BUY, STANCE_NEUTRAL, STANCE_SELL})

    def test_macd_buy_or_sell_only(self, ohlcv_df):
        stance = compute_strategy_stance(ohlcv_df, "macd", {})
        assert STANCE_NEUTRAL not in stance.values

    def test_rsi_stance_valid_labels(self, ohlcv_df):
        stance = compute_strategy_stance(ohlcv_df, "rsi", {})
        assert set(stance.unique()).issubset({STANCE_BUY, STANCE_NEUTRAL, STANCE_SELL})
