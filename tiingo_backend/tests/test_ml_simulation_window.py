import pytest

from features.backtesting.engine import run_backtest_with_signals, run_buy_and_hold_benchmark
from features.ml.labels import build_forward_return_labels
from features.ml.predictor import run_walk_forward_prediction
from features.ml.price_features import build_price_feature_matrix
from features.ml.signals import probabilities_to_signals
from features.ml.simulation_window import (
    build_evaluation_metadata,
    build_simulation_metadata,
    find_bar_index_by_date,
    resolve_evaluation_start_index,
    slice_simulation_window,
    walk_forward_simulation_start_index,
)


def _bars(count: int) -> list[dict]:
    from datetime import datetime, timedelta, timezone

    rows = []
    for i in range(count):
        price = 100 + i * 0.5
        rows.append(
            {
                "time": datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def test_walk_forward_simulation_start_index_returns_train_bars():
    assert walk_forward_simulation_start_index(252) == 252


def test_walk_forward_simulation_start_index_rejects_invalid():
    with pytest.raises(ValueError, match="train_bars"):
        walk_forward_simulation_start_index(0)


def test_slice_simulation_window_preserves_alignment():
    bars = _bars(10)
    signals = ["hold"] * 10
    sliced_bars, sliced_signals = slice_simulation_window(bars, signals, 3)
    assert len(sliced_bars) == 7
    assert len(sliced_signals) == 7
    assert sliced_bars[0]["close"] == bars[3]["close"]
    assert sliced_signals[0] == "hold"


def test_slice_simulation_window_validates_lengths():
    with pytest.raises(ValueError, match="Signal count"):
        slice_simulation_window(_bars(5), ["hold"] * 4, 1)


def test_slice_simulation_window_rejects_out_of_range_start():
    with pytest.raises(ValueError, match="start_index"):
        slice_simulation_window(_bars(5), ["hold"] * 5, 5)


def test_build_simulation_metadata_uses_bar_date():
    bars = _bars(300)
    meta = build_simulation_metadata(
        bars=bars,
        start_index=252,
        decision_timeframe="1d",
    )
    assert meta["simulation_start_bar_index"] == 252
    assert meta["pre_oos_bars_excluded"] == 252
    assert meta["simulation_start_date"] == "2020-09-09"


def test_walk_forward_simulation_starts_at_train_bars():
    train_bars = 120
    test_bars = 40
    bars = _bars(500)
    _, feature_rows = build_price_feature_matrix(bars)
    labels = build_forward_return_labels(bars, label_horizon=5)

    walk_forward = run_walk_forward_prediction(
        model_type="ml_logistic",
        params={},
        feature_rows=feature_rows,
        labels=labels,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=test_bars,
    )
    signals = probabilities_to_signals(walk_forward.probabilities, 0.55, 0.45)
    sim_start = walk_forward_simulation_start_index(train_bars)
    bars_for_sim, signals_for_sim = slice_simulation_window(bars, signals, sim_start)

    strategy = run_backtest_with_signals(
        bars_for_sim,
        signals_for_sim,
        initial_cash=10_000.0,
        commission_bps=0.0,
        decision_timeframe="1d",
    )
    benchmark = run_buy_and_hold_benchmark(
        bars_for_sim,
        initial_cash=10_000.0,
        commission_bps=0.0,
        decision_timeframe="1d",
    )

    assert strategy.equity_curve[0].date == "2020-04-30"
    assert benchmark.equity_curve[0].date == strategy.equity_curve[0].date
    for trade in strategy.trades:
        assert trade.entry_date >= "2020-04-30"

    full_strategy = run_backtest_with_signals(
        bars,
        signals,
        initial_cash=10_000.0,
        commission_bps=0.0,
        decision_timeframe="1d",
    )
    assert full_strategy.equity_curve[0].date == "2020-01-01"
    assert strategy.equity_curve[0].date != full_strategy.equity_curve[0].date


def test_find_bar_index_by_date_matches_daily_bar():
    bars = _bars(10)
    assert find_bar_index_by_date(bars, "2020-01-05", "1d") == 4


def test_resolve_evaluation_start_index_uses_signal_bar_before_entry():
    bars = _bars(80)
    signals = ["hold"] * 50 + ["buy"] + ["hold"] * 29
    strategy = run_backtest_with_signals(
        bars,
        signals,
        initial_cash=10_000.0,
        commission_bps=0.0,
        decision_timeframe="1d",
    )
    assert len(strategy.trades) >= 1
    assert resolve_evaluation_start_index(
        bars,
        strategy.trades,
        decision_timeframe="1d",
    ) == 50


def test_resolve_evaluation_start_index_returns_zero_without_trades():
    bars = _bars(20)
    assert resolve_evaluation_start_index(bars, [], decision_timeframe="1d") == 0


def test_build_evaluation_metadata_includes_reason():
    bars = _bars(60)
    meta = build_evaluation_metadata(
        bars=bars,
        start_index=50,
        decision_timeframe="1d",
        reason="first_trade",
    )
    assert meta["evaluation_start_bar_index"] == 50
    assert meta["evaluation_start_date"] == "2020-02-20"
    assert meta["evaluation_reason"] == "first_trade"


def _apply_evaluation_window(bars, signals, initial_cash=10_000.0):
    strategy = run_backtest_with_signals(
        bars,
        signals,
        initial_cash,
        commission_bps=0.0,
        decision_timeframe="1d",
    )
    eval_offset = resolve_evaluation_start_index(
        bars,
        strategy.trades,
        decision_timeframe="1d",
    )
    if eval_offset > 0:
        eval_bars, eval_signals = slice_simulation_window(bars, signals, eval_offset)
        strategy = run_backtest_with_signals(
            eval_bars,
            eval_signals,
            initial_cash,
            commission_bps=0.0,
            decision_timeframe="1d",
        )
        benchmark = run_buy_and_hold_benchmark(
            eval_bars,
            initial_cash,
            commission_bps=0.0,
            decision_timeframe="1d",
        )
    else:
        benchmark = run_buy_and_hold_benchmark(
            bars,
            initial_cash,
            commission_bps=0.0,
            decision_timeframe="1d",
        )
    return strategy, benchmark, eval_offset


def test_evaluation_window_aligns_benchmark_with_first_trade():
    bars = _bars(80)
    signals = ["hold"] * 50 + ["buy"] + ["hold"] * 29

    full_benchmark = run_buy_and_hold_benchmark(
        bars,
        initial_cash=10_000.0,
        commission_bps=0.0,
        decision_timeframe="1d",
    )
    strategy, benchmark, eval_offset = _apply_evaluation_window(bars, signals)

    assert eval_offset == 50
    assert strategy.equity_curve[0].date == benchmark.equity_curve[0].date
    assert strategy.trades[0].entry_date[:10] >= strategy.equity_curve[0].date[:10]

    full_bh_return = (
        (full_benchmark.final_equity - 10_000.0) / 10_000.0
    ) * 100.0
    trimmed_bh_return = (
        (benchmark.final_equity - 10_000.0) / 10_000.0
    ) * 100.0
    assert trimmed_bh_return < full_bh_return
