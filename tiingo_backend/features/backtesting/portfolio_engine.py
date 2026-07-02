from dataclasses import dataclass
from datetime import date, datetime, timezone

from features.backtesting.portfolio_simulator import (
    MultiAssetEquityPoint,
    MultiAssetPortfolioState,
    MultiAssetSimulationResult,
    MultiAssetTradeRecord,
    force_liquidate_symbol,
    mark_multi_equity,
    rebalance_to_targets,
)
from features.backtesting.returns_panel import ReturnsPanel
from features.portfolio.kelly import capped_kelly_budget, kelly_from_trade_pnls


@dataclass
class PortfolioSizingConfig:
    sizing_method: str = "fixed_fraction"
    allocation_pct: float = 100.0
    max_position_pct: float = 100.0
    kelly_fraction: float = 0.25
    hrp_lookback_bars: int = 252
    rebalance_frequency: int = 21
    target_weights: dict[str, float] | None = None


def _format_bar_date(bar: dict) -> str:
    t = bar["time"]
    if isinstance(t, datetime):
        dt = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    if isinstance(t, date):
        return t.isoformat()
    return str(t)


def _prices_at_index(panel: ReturnsPanel, index: int) -> dict[str, float]:
    return {
        sym: float(panel.bars_by_symbol[sym][index]["close"])
        for sym in panel.symbols
    }


def _open_prices_at_index(panel: ReturnsPanel, index: int) -> dict[str, float]:
    return {
        sym: float(panel.bars_by_symbol[sym][index]["open"])
        for sym in panel.symbols
    }


def _last_bar_index_by_symbol(panel: ReturnsPanel) -> dict[str, int]:
    return {sym: len(panel.bars_by_symbol[sym]) - 1 for sym in panel.symbols}


def _buy_budget(
    state: MultiAssetPortfolioState,
    equity: float,
    sym: str,
    sizing: PortfolioSizingConfig,
    trade_pnls: list[float],
) -> float:
    if sizing.sizing_method == "kelly" and trade_pnls:
        win_rate, avg_win, avg_loss = kelly_from_trade_pnls(trade_pnls)
        budget = capped_kelly_budget(
            equity,
            win_rate,
            avg_win,
            avg_loss,
            kelly_cap=sizing.kelly_fraction,
            max_position_pct=sizing.max_position_pct,
        )
        return budget

    if sizing.target_weights and sym in sizing.target_weights:
        weight = sizing.target_weights[sym]
        return min(
            equity * weight,
            equity * (sizing.max_position_pct / 100.0),
        )

    return min(
        equity * (sizing.allocation_pct / 100.0),
        equity * (sizing.max_position_pct / 100.0),
    )


def run_portfolio_backtest(
    panel: ReturnsPanel,
    signals_by_symbol: dict[str, list[str]],
    *,
    initial_cash: float,
    commission_bps: float,
    slippage_bps: float = 0.0,
    sizing: PortfolioSizingConfig | None = None,
    delisted_symbols: dict[str, float] | None = None,
) -> MultiAssetSimulationResult:
    sizing = sizing or PortfolioSizingConfig()
    state = MultiAssetPortfolioState(cash=initial_cash)
    trades: list[MultiAssetTradeRecord] = []
    equity_curve: list[MultiAssetEquityPoint] = []
    peak_equity = initial_cash
    bar_count = len(panel.dates)
    last_indices = _last_bar_index_by_symbol(panel)
    delisted = delisted_symbols or {}
    trade_pnls: list[float] = []

    pending_signals: dict[str, str] = {}

    for index in range(bar_count):
        open_prices = _open_prices_at_index(panel, index)

        for sym in list(state.positions.keys()):
            if index == last_indices.get(sym):
                settlement = delisted.get(sym, open_prices.get(sym, 0.0))
                force_liquidate_symbol(
                    state,
                    sym,
                    settlement,
                    panel.bars_by_symbol[sym][index],
                    commission_bps,
                    trades,
                    slippage_bps,
                )

        if sizing.target_weights and index % sizing.rebalance_frequency == 0:
            rebalance_to_targets(
                state,
                sizing.target_weights,
                open_prices,
                panel.bars_by_symbol[panel.symbols[0]][index],
                commission_bps,
                trades,
                slippage_bps,
            )

        for sym, signal in pending_signals.items():
            if sym not in panel.symbols:
                continue
            price = open_prices.get(sym, 0.0)
            if price <= 0:
                continue
            bar = panel.bars_by_symbol[sym][index]
            normalized = signal.lower()
            if normalized == "buy" and state.positions.get(sym, 0.0) <= 0:
                equity, _ = mark_multi_equity(state, open_prices, peak_equity)
                budget = _buy_budget(state, equity, sym, sizing, trade_pnls)
                from features.backtesting.portfolio_simulator import buy_qty

                buy_qty(
                    state, sym, budget / price, price, bar,
                    commission_bps, slippage_bps,
                )
            elif normalized == "sell" and state.positions.get(sym, 0.0) > 0:
                from features.backtesting.portfolio_simulator import sell_qty

                prev_trades = len(trades)
                sell_qty(
                    state, sym, state.positions[sym], price, bar,
                    commission_bps, trades, slippage_bps,
                )
                if len(trades) > prev_trades:
                    trade_pnls.append(trades[-1].pnl)
        pending_signals = {}

        close_prices = _prices_at_index(panel, index)
        for sym in panel.symbols:
            if sym in signals_by_symbol and index < len(signals_by_symbol[sym]):
                pending_signals[sym] = signals_by_symbol[sym][index]

        equity, drawdown = mark_multi_equity(state, close_prices, peak_equity)
        peak_equity = max(peak_equity, equity)
        positions_value = equity - state.cash
        equity_curve.append(
            MultiAssetEquityPoint(
                date=_format_bar_date(panel.bars_by_symbol[panel.symbols[0]][index]),
                equity=round(equity, 2),
                cash=round(state.cash, 2),
                positions_value=round(positions_value, 2),
                drawdown_pct=round(drawdown, 2),
            )
        )

    return MultiAssetSimulationResult(
        equity_curve=equity_curve,
        trades=trades,
        final_equity=equity_curve[-1].equity if equity_curve else initial_cash,
    )
