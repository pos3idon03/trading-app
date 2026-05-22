from dataclasses import asdict
from datetime import datetime, timezone

from features.backtesting.bar_context import MultiTimeframeContext
from features.backtesting.simulator import (
    EquityPoint,
    PortfolioState,
    SimulationResult,
    TradeRecord,
    apply_corporate_actions,
    buy_all_in,
    mark_equity,
    sell_all,
)
from features.backtesting.strategies.registry import get_signal_fn
from features.market_data.ohlcv_resample import DAILY_PLUS_TIMEFRAMES

IMMEDIATE_ENTRY_STRATEGIES = {"buy_and_hold"}
ENSEMBLE_STRATEGY = "strategy_ensemble"


def run_backtest(
    bars: list[dict],
    strategy_id: str,
    params: dict,
    initial_cash: float,
    commission_bps: float,
    bar_context: MultiTimeframeContext | None = None,
    decision_timeframe: str = "1d",
) -> SimulationResult:
    signal_fn = get_signal_fn(strategy_id)
    state = PortfolioState(cash=initial_cash)
    trades: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []
    pending_action: str | None = None
    peak_equity = initial_cash
    indicators: list[str | None] = []

    decision_bars = bar_context.decision_bars if bar_context else bars

    for index, bar in enumerate(decision_bars):
        apply_corporate_actions(state, bar)
        _execute_pending(state, bar, pending_action, commission_bps, trades)
        pending_action = None

        if strategy_id in IMMEDIATE_ENTRY_STRATEGIES and index == 0 and state.shares == 0:
            buy_all_in(state, float(bar["open"]), bar, commission_bps)

        signal = _generate_signal(
            strategy_id,
            signal_fn,
            bars,
            indicators,
            params,
            index,
            bar_context,
        )
        pending_action = _resolve_pending(signal, state)

        equity, drawdown = mark_equity(state, bar, peak_equity)
        peak_equity = max(peak_equity, equity)
        equity_curve.append(
            EquityPoint(
                date=_format_bar_date(bar, decision_timeframe),
                equity=round(equity, 2),
                cash=round(state.cash, 2),
                shares=round(state.shares, 6),
                drawdown_pct=round(drawdown, 2),
            )
        )

    return SimulationResult(
        equity_curve=equity_curve,
        trades=trades,
        final_equity=equity_curve[-1].equity if equity_curve else initial_cash,
    )


def run_buy_and_hold_benchmark(
    bars: list[dict],
    initial_cash: float,
    commission_bps: float,
    decision_timeframe: str = "1d",
) -> SimulationResult:
    state = PortfolioState(cash=initial_cash)
    trades: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []
    peak_equity = initial_cash
    entered = False

    for bar in bars:
        apply_corporate_actions(state, bar)
        if not entered and float(bar["open"]) > 0:
            buy_all_in(state, float(bar["open"]), bar, commission_bps)
            entered = True

        equity, drawdown = mark_equity(state, bar, peak_equity)
        peak_equity = max(peak_equity, equity)
        equity_curve.append(
            EquityPoint(
                date=_format_bar_date(bar, decision_timeframe),
                equity=round(equity, 2),
                cash=round(state.cash, 2),
                shares=round(state.shares, 6),
                drawdown_pct=round(drawdown, 2),
            )
        )

    return SimulationResult(
        equity_curve=equity_curve,
        trades=trades,
        final_equity=equity_curve[-1].equity if equity_curve else initial_cash,
    )


def serialize_simulation(result: SimulationResult) -> dict:
    return {
        "equity_curve": [asdict(point) for point in result.equity_curve],
        "trades": [asdict(trade) for trade in result.trades],
        "final_equity": result.final_equity,
    }


def _generate_signal(
    strategy_id: str,
    signal_fn,
    bars: list[dict],
    indicators: list[str | None],
    params: dict,
    index: int,
    bar_context: MultiTimeframeContext | None,
) -> str:
    if strategy_id == ENSEMBLE_STRATEGY:
        from features.backtesting.strategies import ensemble as ensemble_strategy

        return ensemble_strategy.generate_signal_at(
            bars,
            indicators,
            params,
            index,
            bar_context,
        )

    if bar_context is None:
        return signal_fn(bars, indicators, params, index)

    signal_tf = bar_context.standalone_signal_timeframe
    aligned = bar_context.aligned_index(index, signal_tf)
    if aligned < 0:
        return "hold"
    signal_bars = bar_context.bars_for(signal_tf)
    return signal_fn(signal_bars, indicators, params, aligned)


def _execute_pending(
    state: PortfolioState,
    bar: dict,
    pending_action: str | None,
    commission_bps: float,
    trades: list[TradeRecord],
) -> None:
    price = float(bar["open"])
    if pending_action == "buy" and state.shares == 0:
        buy_all_in(state, price, bar, commission_bps)
    elif pending_action == "sell" and state.shares > 0:
        sell_all(state, price, bar, commission_bps, trades)


def _resolve_pending(signal: str, state: PortfolioState) -> str | None:
    if signal == "buy" and state.shares == 0:
        return "buy"
    if signal == "sell" and state.shares > 0:
        return "sell"
    return None


def _format_bar_date(bar: dict, decision_timeframe: str) -> str:
    t = bar["time"]
    if decision_timeframe in DAILY_PLUS_TIMEFRAMES:
        if hasattr(t, "date"):
            return t.date().isoformat()
        return str(t)[:10]
    if isinstance(t, datetime):
        dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    return str(t)
