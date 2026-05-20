"""Combine walk-forward MC prob stance with classic algo strategy stances."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from features.backtesting.multi_timeframe_combo import (
    align_stance_to_execution,
    resample_ohlcv_df,
)
from features.backtesting.stance import (
    STANCE_BUY,
    STANCE_NEUTRAL,
    STANCE_SELL,
    build_signal_timeline_from_stance,
    combine_stances,
    compute_strategy_stance,
)
from utils.timeframes import normalize_timeframe

MC_COMBO_LEG_NAME = "mc_prob"


@dataclass
class AlgoComboLeg:
    strategy_name: str
    strategy_params: dict
    weight: float = 1.0
    timeframe: str = "1d"


def prob_to_stance(
    prob: float | None,
    buy_threshold: float,
    sell_threshold: float,
) -> str:
    """Map MC effective prob to Buy / Neutral / Sell stance."""
    if prob is None:
        return STANCE_NEUTRAL
    if prob >= buy_threshold:
        return STANCE_BUY
    if prob < sell_threshold:
        return STANCE_SELL
    return STANCE_NEUTRAL


def build_mc_stance_series(
    eval_df: pd.DataFrame,
    effective_probs: list[float | None],
    buy_threshold: float,
    sell_threshold: float,
) -> pd.Series:
    """Build MC prob leg stance aligned to eval_df index."""
    stances = [
        prob_to_stance(p, buy_threshold, sell_threshold) for p in effective_probs
    ]
    return pd.Series(stances, index=eval_df.index, dtype=object)


def _stance_for_leg(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    leg: AlgoComboLeg,
    exec_timeframe: str,
) -> pd.Series:
    """Compute algo stance on full history and align to eval bars."""
    leg_tf = normalize_timeframe(leg.timeframe or exec_timeframe)
    exec_tf = normalize_timeframe(exec_timeframe)
    source_df = resample_ohlcv_df(full_df, leg_tf) if leg_tf != exec_tf else full_df
    stance = compute_strategy_stance(source_df, leg.strategy_name, leg.strategy_params)
    return align_stance_to_execution(stance, source_df, eval_df)


def build_algo_stance_list(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    algo_entries: list[AlgoComboLeg],
    exec_timeframe: str,
) -> list[pd.Series]:
    """Per-algo stance series aligned to eval_df."""
    return [
        _stance_for_leg(full_df, eval_df, leg, exec_timeframe)
        for leg in algo_entries
    ]


def combine_mc_algo_stances(
    mc_stance: pd.Series,
    algo_stances: list[pd.Series],
    mode: str,
    mc_weight: float,
    algo_weights: list[float],
    threshold: float,
) -> pd.Series:
    """Combine MC + algo stances into boolean long-position series."""
    weights = [mc_weight, *algo_weights]
    stance_list = [mc_stance, *algo_stances]
    return combine_stances(stance_list, mode, weights, threshold)


def combined_position_to_stance(combined: pd.Series) -> pd.Series:
    """Map boolean position to Buy/Neutral for timeline display."""
    out = pd.Series(STANCE_NEUTRAL, index=combined.index, dtype=object)
    out[combined.astype(bool)] = STANCE_BUY
    return out


def position_series_to_actions(
    combined: pd.Series,
    entry_confirmation_bars: int,
    min_hold_bars: int,
    cooldown_bars: int,
) -> list[str]:
    """Apply entry filters to combined long/flat target series."""
    actions: list[str] = []
    in_position = False
    bars_in_position = 0
    bars_since_sell = cooldown_bars
    consecutive_entry_bars = 0

    for i in range(len(combined)):
        want_long = bool(combined.iloc[i])
        action = "FLAT"

        if not in_position:
            if bars_since_sell < cooldown_bars:
                action = "FLAT"
            elif want_long:
                streak = consecutive_entry_bars + 1
                if streak >= entry_confirmation_bars:
                    action = "BUY"
                    consecutive_entry_bars = 0
                else:
                    action = "FLAT"
                    consecutive_entry_bars = streak
            else:
                consecutive_entry_bars = 0
        elif bars_in_position < min_hold_bars:
            action = "FLAT"
        elif not want_long:
            action = "SELL"
        else:
            action = "FLAT"

        actions.append(action)
        if action == "BUY":
            in_position = True
            bars_in_position = 0
            bars_since_sell = 0
        elif action == "SELL":
            in_position = False
            bars_in_position = 0
            bars_since_sell = 0
        else:
            if in_position:
                bars_in_position += 1
            bars_since_sell += 1

    return actions


def build_combo_signal_timelines(
    eval_df: pd.DataFrame,
    mc_stance: pd.Series,
    algo_entries: list[AlgoComboLeg],
    algo_stances: list[pd.Series],
    combined: pd.Series,
) -> tuple[list[dict], list[dict]]:
    """Build per-leg and combined signal timelines for API response."""
    legs: list[dict] = [{
        "strategy_name": MC_COMBO_LEG_NAME,
        "trade_log": [],
        "indicator_series": [],
        "equity_curve": [],
        "buy_hold_curve": [],
        "signal_timeline": build_signal_timeline_from_stance(eval_df, mc_stance),
    }]
    for leg, stance in zip(algo_entries, algo_stances):
        legs.append({
            "strategy_name": leg.strategy_name,
            "trade_log": [],
            "indicator_series": [],
            "equity_curve": [],
            "buy_hold_curve": [],
            "signal_timeline": build_signal_timeline_from_stance(eval_df, stance),
        })
    combined_timeline = build_signal_timeline_from_stance(
        eval_df, combined_position_to_stance(combined),
    )
    return legs, combined_timeline


def generate_combo_actions(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    effective_probs: list[float | None],
    buy_threshold: float,
    sell_threshold: float,
    exec_timeframe: str,
    algo_entries: list[AlgoComboLeg],
    combination_mode: str,
    mc_weight: float,
    threshold: float,
    entry_confirmation_bars: int,
    min_hold_bars: int,
    cooldown_bars: int,
) -> tuple[list[str], list[dict], list[dict]]:
    """Build combined actions and combo signal timelines."""
    mc_stance = build_mc_stance_series(
        eval_df, effective_probs, buy_threshold, sell_threshold,
    )
    algo_stances = build_algo_stance_list(
        full_df, eval_df, algo_entries, exec_timeframe,
    )
    algo_weights = [leg.weight for leg in algo_entries]
    combined = combine_mc_algo_stances(
        mc_stance, algo_stances, combination_mode, mc_weight, algo_weights, threshold,
    )
    actions = position_series_to_actions(
        combined, entry_confirmation_bars, min_hold_bars, cooldown_bars,
    )
    combo_signals, combined_timeline = build_combo_signal_timelines(
        eval_df, mc_stance, algo_entries, algo_stances, combined,
    )
    return actions, combo_signals, combined_timeline
