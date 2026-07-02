from features.backtesting.engine import run_backtest_with_signals, run_buy_and_hold_benchmark
from features.backtesting.metrics import compute_metrics
from features.backtesting.trade_exits import TradeExitConfig
from features.ml.evaluation import compute_classification_metrics
from features.ml.signals import count_signals, predictions_to_signals
from features.ml.simulation_window import (
    slice_simulation_window,
    walk_forward_simulation_start_index,
)


def ternary_threshold_gates(min_class_probability: float | None) -> list[float | None]:
    if min_class_probability is not None:
        return [min_class_probability]
    return [None, 0.55, 0.6]


def binary_threshold_combos(
    buy_thresholds: list[float],
    sell_thresholds: list[float],
) -> list[tuple[float, float]]:
    combos: list[tuple[float, float]] = []
    for buy_threshold in buy_thresholds:
        for sell_threshold in sell_thresholds:
            if buy_threshold > sell_threshold:
                combos.append((buy_threshold, sell_threshold))
    return combos


def threshold_sort_key(row: dict) -> tuple:
    pf = row.get("profit_factor")
    pf_val = float(pf) if pf is not None else -1.0
    return (
        pf_val,
        row.get("total_return_pct") or -1e9,
        row.get("sharpe_ratio") or -1e9,
        row.get("f1_macro") or 0.0,
    )


def evaluate_ternary_threshold_gate(
    *,
    label_mode: str,
    probabilities: list[float | None],
    class_predictions: list[int | None],
    class_probabilities: list[list[float] | None],
    y_true: list[int],
    gate: float | None,
) -> dict:
    signals = predictions_to_signals(
        label_mode=label_mode,
        probabilities=probabilities,
        class_predictions=class_predictions,
        buy_threshold=0.55,
        sell_threshold=0.45,
        min_class_probability=gate,
        class_probabilities=class_probabilities,
    )
    aligned_true: list[int] = []
    aligned_pred: list[int] = []
    for truth, pred in zip(y_true, class_predictions):
        if pred is None:
            continue
        aligned_true.append(truth)
        aligned_pred.append(pred)
    metrics = compute_classification_metrics(aligned_true, aligned_pred)
    return {
        "buy_threshold": None,
        "sell_threshold": None,
        "min_class_probability": gate,
        "signal_counts": count_signals(signals),
        **metrics,
    }


def evaluate_binary_threshold_combo(
    *,
    label_mode: str,
    probabilities: list[float | None],
    y_true: list[int],
    y_proba: list[list[float]],
    buy_threshold: float,
    sell_threshold: float,
) -> dict:
    signals = predictions_to_signals(
        label_mode=label_mode,
        probabilities=probabilities,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
    )
    if y_true and y_proba:
        aligned_true = y_true
        aligned_pred = [
            1 if prob >= 0.5 else 0
            for prob in [row[1] if len(row) > 1 else row[0] for row in y_proba]
        ]
    else:
        aligned_true = []
        aligned_pred = []
        for index, prob in enumerate(probabilities):
            if prob is None:
                continue
            if index >= len(y_true):
                break
            aligned_true.append(y_true[index] if index < len(y_true) else 0)
            aligned_pred.append(1 if prob >= 0.5 else 0)
    metrics = compute_classification_metrics(aligned_true, aligned_pred)
    return {
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold,
        "min_class_probability": None,
        "signal_counts": count_signals(signals),
        **metrics,
    }


def evaluate_binary_threshold_pnl(
    *,
    bars: list[dict],
    probabilities: list[float | None],
    label_mode: str,
    buy_threshold: float,
    sell_threshold: float,
    y_true: list[int],
    y_proba: list[list[float]],
    train_bars: int,
    initial_cash: float,
    commission_bps: float,
    slippage_bps: float,
    exit_config: TradeExitConfig,
    decision_timeframe: str = "1d",
    asset_type: str = "equity",
) -> dict:
    signals = predictions_to_signals(
        label_mode=label_mode,
        probabilities=probabilities,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
    )
    sim_start = walk_forward_simulation_start_index(train_bars)
    sim_bars, sim_signals = slice_simulation_window(bars, signals, sim_start)

    strategy = run_backtest_with_signals(
        sim_bars,
        sim_signals,
        initial_cash,
        commission_bps,
        decision_timeframe=decision_timeframe,
        slippage_bps=slippage_bps,
        exit_config=exit_config,
    )
    benchmark = run_buy_and_hold_benchmark(
        sim_bars,
        initial_cash,
        commission_bps,
        decision_timeframe=decision_timeframe,
        slippage_bps=slippage_bps,
    )
    portfolio = compute_metrics(
        strategy,
        benchmark,
        initial_cash,
        decision_timeframe,
        asset_type=asset_type,
    )

    cls = evaluate_binary_threshold_combo(
        label_mode=label_mode,
        probabilities=probabilities,
        y_true=y_true,
        y_proba=y_proba,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
    )
    return {
        **cls,
        "profit_factor": portfolio.get("profit_factor"),
        "total_return_pct": portfolio.get("total_return_pct"),
        "max_drawdown_pct": portfolio.get("max_drawdown_pct"),
        "sharpe_ratio": portfolio.get("sharpe_ratio"),
        "trade_count": portfolio.get("trade_count"),
        "alpha_pct": portfolio.get("alpha_pct"),
    }


def run_threshold_search(
    *,
    label_mode: str,
    probabilities: list[float | None],
    class_predictions: list[int | None],
    class_probabilities: list[list[float] | None],
    y_true: list[int],
    y_proba: list[list[float]],
    buy_thresholds: list[float],
    sell_thresholds: list[float],
    min_class_probability: float | None = None,
) -> list[dict]:
    if label_mode == "ternary":
        return [
            evaluate_ternary_threshold_gate(
                label_mode=label_mode,
                probabilities=probabilities,
                class_predictions=class_predictions,
                class_probabilities=class_probabilities,
                y_true=y_true,
                gate=gate,
            )
            for gate in ternary_threshold_gates(min_class_probability)
        ]

    results = [
        evaluate_binary_threshold_combo(
            label_mode=label_mode,
            probabilities=probabilities,
            y_true=y_true,
            y_proba=y_proba,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
        )
        for buy_threshold, sell_threshold in binary_threshold_combos(
            buy_thresholds,
            sell_thresholds,
        )
    ]
    results.sort(key=threshold_sort_key, reverse=True)
    return results
