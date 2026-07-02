from features.backtesting.trade_exits import TradeExitConfig
from features.ml.threshold_search import (
    evaluate_binary_threshold_pnl,
    threshold_sort_key,
)


def _bars(count: int) -> list[dict]:
    rows = []
    for index in range(count):
        close = 100.0 + index * 0.5
        rows.append(
            {
                "time": f"2024-01-{index + 1:02d}",
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1_000_000,
            }
        )
    return rows


def test_threshold_pnl_differs_by_buy_threshold():
    bars = _bars(80)
    probabilities = [None] * 20 + [0.7] * 20 + [0.3] * 20 + [0.65] * 20
    exit_config = TradeExitConfig(
        policy="label_horizon",
        max_hold_bars=5,
        profit_atr_mult=2.0,
        stop_atr_mult=1.5,
        atr_period=14,
    )
    high_buy = evaluate_binary_threshold_pnl(
        bars=bars,
        probabilities=probabilities,
        label_mode="binary",
        buy_threshold=0.55,
        sell_threshold=0.45,
        y_true=[],
        y_proba=[],
        train_bars=10,
        initial_cash=10_000.0,
        commission_bps=0.0,
        slippage_bps=0.0,
        exit_config=exit_config,
    )
    low_buy = evaluate_binary_threshold_pnl(
        bars=bars,
        probabilities=probabilities,
        label_mode="binary",
        buy_threshold=0.9,
        sell_threshold=0.45,
        y_true=[],
        y_proba=[],
        train_bars=10,
        initial_cash=10_000.0,
        commission_bps=0.0,
        slippage_bps=0.0,
        exit_config=exit_config,
    )
    assert high_buy["trade_count"] != low_buy["trade_count"]


def test_threshold_sort_key_prefers_profit_factor():
    rows = [
        {"profit_factor": 1.2, "total_return_pct": 1.0, "sharpe_ratio": 0.1, "f1_macro": 0.5},
        {"profit_factor": 0.8, "total_return_pct": 5.0, "sharpe_ratio": 2.0, "f1_macro": 0.9},
    ]
    sorted_rows = sorted(rows, key=threshold_sort_key, reverse=True)
    assert sorted_rows[0]["profit_factor"] == 1.2
