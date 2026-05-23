from datetime import datetime, timedelta, timezone

import pytest

from features.backtesting.engine import run_backtest, run_backtest_with_signals, run_buy_and_hold_benchmark
from features.backtesting.metrics import compute_metrics
from features.backtesting.simulator import EquityPoint, SimulationResult, TradeRecord


def _bars(count: int, start_price: float = 100.0, step: float = 1.0) -> list[dict]:
    rows = []
    for i in range(count):
        price = start_price + (i * step)
        rows.append(
            {
                "time": datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def test_run_backtest_with_signals_executes_trades():
    bars = _bars(5, start_price=100.0, step=0.0)
    signals = ["buy", "hold", "hold", "sell", "hold"]
    result = run_backtest_with_signals(bars, signals, 10_000.0, 0.0)
    assert len(result.equity_curve) == len(bars)
    assert len(result.trades) == 1


def test_run_backtest_with_signals_length_mismatch_raises():
    bars = _bars(3)
    with pytest.raises(ValueError):
        run_backtest_with_signals(bars, ["buy"], 10_000.0, 0.0)


def test_buy_and_hold_matches_benchmark_on_uptrend():
    bars = _bars(10, start_price=100.0, step=2.0)
    strategy = run_backtest(bars, "buy_and_hold", {}, 10_000.0, 0.0)
    benchmark = run_buy_and_hold_benchmark(bars, 10_000.0, 0.0)
    assert strategy.final_equity == pytest.approx(benchmark.final_equity, rel=1e-6)
    assert len(strategy.trades) == 0


def test_sma_crossover_generates_round_trips_on_oscillating_series():
    prices = [100, 101, 102, 103, 104, 103, 102, 101, 100, 99, 98, 99, 100, 101, 102]
    bars = []
    for i, close in enumerate(prices):
        bars.append(
            {
                "time": datetime(2024, 1, 1 + i, tzinfo=timezone.utc),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": float(close),
                "div_cash": 0,
                "split_factor": 1,
            }
        )

    result = run_backtest(
        bars,
        "sma_crossover",
        {"fast_period": 3, "slow_period": 5},
        10_000.0,
        0.0,
    )
    assert len(result.equity_curve) == len(bars)
    assert result.final_equity > 0


def test_adjusted_split_does_not_inflate_buy_and_hold():
    bars = [
        {
            "time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "div_cash": 0,
            "split_factor": 1,
        },
        {
            "time": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "open": 110.0,
            "high": 111.0,
            "low": 109.0,
            "close": 110.0,
            "div_cash": 0,
            "split_factor": 2.0,
        },
    ]
    result = run_buy_and_hold_benchmark(bars, 10_000.0, 0.0)
    assert result.final_equity == pytest.approx(11_000.0, rel=1e-6)


def test_compute_metrics_includes_alpha():
    bars = _bars(20, start_price=100.0, step=1.0)
    strategy = run_backtest(bars, "buy_and_hold", {}, 10_000.0, 0.0)
    benchmark = run_buy_and_hold_benchmark(bars, 10_000.0, 0.0)
    metrics = compute_metrics(strategy, benchmark, 10_000.0)
    assert metrics["trade_count"] == 0
    assert metrics["alpha_pct"] == pytest.approx(0.0)
    assert metrics["total_return_pct"] is not None
    assert metrics["sortino_ratio"] is not None
    assert metrics["profit_factor"] is None
    assert metrics["calmar_ratio"] is None


def test_compute_metrics_profit_factor_and_calmar():
    curve = [
        EquityPoint(date="2024-01-01", equity=10_000.0, cash=0.0, shares=1.0, drawdown_pct=0.0),
        EquityPoint(date="2024-01-02", equity=10_500.0, cash=0.0, shares=1.0, drawdown_pct=0.0),
        EquityPoint(date="2024-01-03", equity=10_200.0, cash=0.0, shares=1.0, drawdown_pct=-2.86),
        EquityPoint(date="2024-01-04", equity=10_800.0, cash=0.0, shares=1.0, drawdown_pct=0.0),
    ]
    trades = [
        TradeRecord(
            entry_date="2024-01-01",
            exit_date="2024-01-02",
            entry_price=100.0,
            exit_price=110.0,
            shares=10.0,
            pnl=100.0,
            pnl_pct=10.0,
        ),
        TradeRecord(
            entry_date="2024-01-02",
            exit_date="2024-01-03",
            entry_price=110.0,
            exit_price=100.0,
            shares=10.0,
            pnl=-100.0,
            pnl_pct=-9.09,
        ),
    ]
    strategy = SimulationResult(equity_curve=curve, trades=trades, final_equity=10_800.0)
    benchmark = SimulationResult(equity_curve=curve[:2], trades=[], final_equity=10_500.0)
    metrics = compute_metrics(strategy, benchmark, 10_000.0)
    assert metrics["profit_factor"] == pytest.approx(1.0)
    assert metrics["sortino_ratio"] is not None
    assert metrics["calmar_ratio"] is not None
    assert metrics["win_rate_pct"] == pytest.approx(50.0)


def test_compute_metrics_profit_factor_all_wins():
    trades = [
        TradeRecord(
            entry_date="2024-01-01",
            exit_date="2024-01-02",
            entry_price=100.0,
            exit_price=110.0,
            shares=10.0,
            pnl=100.0,
            pnl_pct=10.0,
        ),
    ]
    curve = [
        EquityPoint(date="2024-01-01", equity=10_000.0, cash=0.0, shares=1.0, drawdown_pct=0.0),
        EquityPoint(date="2024-01-02", equity=10_100.0, cash=0.0, shares=1.0, drawdown_pct=0.0),
    ]
    strategy = SimulationResult(equity_curve=curve, trades=trades, final_equity=10_100.0)
    benchmark = strategy
    metrics = compute_metrics(strategy, benchmark, 10_000.0)
    assert metrics["profit_factor"] == pytest.approx(999.0)
