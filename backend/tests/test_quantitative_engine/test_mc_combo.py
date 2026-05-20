"""Tests for MC + algo strategy combo signal generation."""
from datetime import datetime, timezone

import pandas as pd
import pytest

from features.backtesting.stance import STANCE_BUY, STANCE_NEUTRAL, STANCE_SELL
from features.quantitative_engine.mc_combo import (
    AlgoComboLeg,
    build_mc_stance_series,
    combine_mc_algo_stances,
    position_series_to_actions,
    prob_to_stance,
    generate_combo_actions,
)


def _eval_df(n: int = 5) -> pd.DataFrame:
    times = pd.date_range("2024-01-01", periods=n, freq="D", tz=timezone.utc)
    close = [100.0 + i for i in range(n)]
    return pd.DataFrame({
        "time": times,
        "open": close,
        "high": [c + 1 for c in close],
        "low": [c - 1 for c in close],
        "close": close,
        "volume": 1000.0,
    })


class TestProbToStance:
    def test_buy_at_or_above_threshold(self):
        assert prob_to_stance(0.7, 0.65, 0.4) == STANCE_BUY

    def test_sell_below_exit_threshold(self):
        assert prob_to_stance(0.35, 0.65, 0.4) == STANCE_SELL

    def test_neutral_in_mid_band(self):
        assert prob_to_stance(0.5, 0.65, 0.4) == STANCE_NEUTRAL

    def test_none_is_neutral(self):
        assert prob_to_stance(None, 0.65, 0.4) == STANCE_NEUTRAL


class TestCombineMcAlgoStances:
    def test_and_blocks_buy_when_algo_neutral(self):
        idx = pd.date_range("2024-01-01", periods=3, freq="D")
        mc = pd.Series([STANCE_BUY, STANCE_BUY, STANCE_BUY], index=idx)
        algo = pd.Series([STANCE_NEUTRAL, STANCE_BUY, STANCE_SELL], index=idx)
        combined = combine_mc_algo_stances(mc, [algo], "and", 1.0, [1.0], 0.5)
        assert not bool(combined.iloc[0])
        assert bool(combined.iloc[1])


class TestPositionSeriesToActions:
    def test_entry_confirmation_delays_buy(self):
        idx = pd.date_range("2024-01-01", periods=4, freq="D")
        combined = pd.Series([True, True, False, False], index=idx)
        actions = position_series_to_actions(combined, 2, 0, 0)
        assert actions[0] == "FLAT"
        assert actions[1] == "BUY"
        assert actions[2] == "SELL"


class TestGenerateComboActions:
    @pytest.fixture
    def full_df(self):
        n = 80
        times = pd.date_range("2023-01-01", periods=n, freq="D", tz=timezone.utc)
        close = [100.0 + i * 0.1 for i in range(n)]
        return pd.DataFrame({
            "time": times,
            "open": close,
            "high": [c + 0.5 for c in close],
            "low": [c - 0.5 for c in close],
            "close": close,
            "volume": 1000.0,
        })

    def test_produces_combo_signals(self, full_df):
        eval_df = full_df.iloc[-5:].reset_index(drop=True)
        probs = [0.7, 0.7, 0.35, 0.5, 0.6]
        legs = [AlgoComboLeg("rsi", {"period": 14}, weight=1.0, timeframe="1d")]
        actions, combo_signals, combined_tl = generate_combo_actions(
            full_df,
            eval_df,
            probs,
            buy_threshold=0.65,
            sell_threshold=0.40,
            exec_timeframe="1d",
            algo_entries=legs,
            combination_mode="and",
            mc_weight=1.0,
            threshold=0.5,
            entry_confirmation_bars=1,
            min_hold_bars=0,
            cooldown_bars=0,
        )
        assert len(actions) == 5
        assert combo_signals[0]["strategy_name"] == "mc_prob"
        assert combo_signals[1]["strategy_name"] == "rsi"
        assert len(combined_tl) == 5

    def test_mc_stance_series(self):
        eval_df = _eval_df(3)
        mc = build_mc_stance_series(eval_df, [0.7, 0.5, 0.3], 0.65, 0.4)
        assert mc.iloc[0] == STANCE_BUY
        assert mc.iloc[1] == STANCE_NEUTRAL
        assert mc.iloc[2] == STANCE_SELL
