"""Adapt multi-asset simulation results for single-asset metrics."""

from features.backtesting.portfolio_simulator import MultiAssetSimulationResult
from features.backtesting.simulator import EquityPoint, SimulationResult, TradeRecord


def portfolio_to_simulation_result(
    portfolio: MultiAssetSimulationResult,
) -> SimulationResult:
    curve = [
        EquityPoint(
            date=p.date,
            equity=p.equity,
            cash=p.cash,
            position_value=p.positions_value,
            drawdown_pct=p.drawdown_pct,
        )
        for p in portfolio.equity_curve
    ]
    trades = [
        TradeRecord(
            entry_date=t.entry_date,
            exit_date=t.exit_date,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            qty=t.qty,
            pnl=t.pnl,
            return_pct=t.return_pct,
        )
        for t in portfolio.trades
    ]
    return SimulationResult(
        equity_curve=curve,
        trades=trades,
        final_equity=portfolio.final_equity,
    )
