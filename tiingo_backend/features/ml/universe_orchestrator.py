"""Multi-symbol ML universe backtest orchestration."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal
from features.backtesting.metrics import compute_metrics
from features.backtesting.portfolio_engine import PortfolioSizingConfig, run_portfolio_backtest
from features.backtesting.portfolio_metrics import portfolio_to_simulation_result
from features.backtesting.returns_panel import build_return_matrix, load_returns_panel
from features.backtesting.survivorship import (
    build_survivorship_warnings,
    delisted_settlement_prices,
)
from features.backtesting.universe_loader import resolve_universe_symbols
from features.portfolio.sizing import compute_target_weights


async def run_universe_ml_backtest(
    session: AsyncSession,
    *,
    universe_id: int | None,
    symbols: list[str] | None,
    signals_by_symbol: dict[str, list[str]],
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    initial_cash: float,
    commission_bps: float,
    slippage_bps: float,
    sizing_params: dict[str, Any],
) -> dict[str, Any]:
    as_of = start.date() if start else date.today()
    resolved, universe_warnings = await resolve_universe_symbols(
        session,
        universe_id=universe_id,
        symbols=symbols,
        as_of=as_of,
    )

    panel = await load_returns_panel(
        session,
        symbols=resolved,
        timeframe=timeframe,
        start=start,
        end=end,
    )

    instruments = {}
    for sym in panel.symbols:
        inst = await instrument_dal.get_by_symbol(session, sym)
        if inst:
            instruments[sym] = inst

    end_date = end.date() if end else (panel.dates[-1] if panel.dates else as_of)
    surv_warnings = build_survivorship_warnings(
        symbols=panel.symbols,
        instruments=instruments,
        bars_by_symbol=panel.bars_by_symbol,
        requested_end=end_date,
    )

    sizing_method = str(sizing_params.get("sizing_method") or "fixed_fraction")
    target_weights = None
    if sizing_method == "hrp":
        matrix = build_return_matrix(
            panel,
            len(panel.dates) - 1,
            int(sizing_params.get("hrp_lookback_bars", 252)),
        )
        target_weights = compute_target_weights(
            "hrp",
            symbols=panel.symbols,
            returns_matrix=matrix,
            linkage_method=str(sizing_params.get("hrp_linkage_method") or "single"),
        )

    sizing = PortfolioSizingConfig(
        sizing_method=sizing_method,
        allocation_pct=float(sizing_params.get("allocation_pct", 100.0)),
        max_position_pct=float(sizing_params.get("max_position_pct", 100.0)),
        kelly_fraction=float(sizing_params.get("kelly_fraction", 0.25)),
        hrp_lookback_bars=int(sizing_params.get("hrp_lookback_bars", 252)),
        rebalance_frequency=int(sizing_params.get("rebalance_frequency", 21)),
        target_weights=target_weights,
    )

    sim = run_portfolio_backtest(
        panel,
        signals_by_symbol,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        sizing=sizing,
        delisted_symbols=delisted_settlement_prices(instruments),
    )

    from features.backtesting.simulator import SimulationResult

    strategy_result = portfolio_to_simulation_result(sim)
    benchmark_result = SimulationResult(
        equity_curve=strategy_result.equity_curve,
        trades=[],
        final_equity=initial_cash,
    )
    portfolio_metrics = compute_metrics(
        strategy_result,
        benchmark_result,
        initial_cash,
        timeframe,
    )

    return {
        "simulation": sim,
        "panel": panel,
        "survivorship_warnings": universe_warnings + panel.warnings + surv_warnings,
        "target_weights": target_weights,
        "symbols": panel.symbols,
        "metrics": portfolio_metrics,
    }
