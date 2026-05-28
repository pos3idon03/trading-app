from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import backtest_dal, instrument_dal
from features.backtesting.bar_loader import load_backtest_bars, validate_timeframe
from features.backtesting.engine import (
    run_backtest_with_signals,
    run_buy_and_hold_benchmark,
    serialize_simulation,
)
from features.backtesting.metrics import compute_metrics
from features.foundation.availability import require_foundation_models
from features.foundation.catalog import (
    get_foundation_model_catalog,
    minimum_bars_required,
    validate_foundation_params,
)
from features.foundation.forecast_metrics import compute_forecast_metrics
from features.foundation.model_cache import get_foundation_adapter
from features.foundation.series_builder import (
    bar_close,
    build_univariate_series,
    format_bar_date,
    sparse_forecast_samples,
)
from features.foundation.signals import count_signals
from features.foundation.walk_forward import run_walk_forward_forecasts, walk_forward_metadata
from features.ml.simulation_window import (
    build_simulation_metadata,
    slice_simulation_window,
)


def get_foundation_catalog() -> list[dict]:
    return get_foundation_model_catalog()


async def preview_foundation_forecast_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
) -> dict:
    require_foundation_models()
    validate_timeframe(timeframe, "decision timeframe")
    validated = validate_foundation_params(model_type, params)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    bars = await load_backtest_bars(
        session,
        instrument["id"],
        timeframe,
        start,
        end,
    )
    min_bars = minimum_bars_required(validated)
    if len(bars) < min_bars:
        raise ValueError(f"Need at least {min_bars} bars; got {len(bars)}")

    series = build_univariate_series(bars, validated["target_series"])
    context_len = int(validated["context_length"])
    horizon = int(validated["forecast_horizon"])
    context = series[-context_len:]
    adapter = get_foundation_adapter(model_type)
    result = adapter.forecast(context, horizon)

    context_start = len(bars) - context_len
    context_points = [
        {
            "date": format_bar_date(bars[i], timeframe),
            "actual": series[i],
            "forecast": None,
            "lower": None,
            "upper": None,
        }
        for i in range(context_start, len(bars))
    ]
    forecast_points = []
    for step, value in enumerate(result.point):
        forecast_points.append(
            {
                "date": f"forecast+{step + 1}",
                "actual": None,
                "forecast": value,
                "lower": result.lower[step] if result.lower else None,
                "upper": result.upper[step] if result.upper else None,
            }
        )

    return {
        "symbol": instrument["symbol"],
        "model_type": model_type,
        "context_points": context_points,
        "forecast_points": forecast_points,
        "context_length": context_len,
        "forecast_horizon": horizon,
    }


async def run_foundation_backtest_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    initial_cash: float,
    commission_bps: float,
    on_progress: Callable[[int], None] | None = None,
) -> dict:
    require_foundation_models()
    validate_timeframe(timeframe, "decision timeframe")
    validated = validate_foundation_params(model_type, params)

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    run = await backtest_dal.create_run(
        session,
        instrument_id=instrument["id"],
        symbol=instrument["symbol"],
        strategy=model_type,
        params=validated,
        timeframe=timeframe,
        start_date=start,
        end_date=end,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
    )
    await session.commit()

    try:
        bars = await load_backtest_bars(
            session,
            instrument["id"],
            timeframe,
            start,
            end,
        )
        min_bars = minimum_bars_required(validated)
        if len(bars) < min_bars:
            raise ValueError(f"Need at least {min_bars} bars; got {len(bars)}")

        series = build_univariate_series(bars, validated["target_series"])
        signal_prices = [bar_close(bar, "close") for bar in bars]
        adapter = get_foundation_adapter(model_type)
        signals, forecasts = run_walk_forward_forecasts(
            series,
            adapter,
            context_length=int(validated["context_length"]),
            forecast_horizon=int(validated["forecast_horizon"]),
            signal_mode=validated["signal_mode"],
            buy_return_threshold=float(validated["buy_return_threshold"]),
            sell_return_threshold=float(validated["sell_return_threshold"]),
            signal_prices=signal_prices,
            on_progress=on_progress,
        )

        sim_start = int(validated["context_length"])
        bars_for_sim, signals_for_sim = slice_simulation_window(bars, signals, sim_start)
        strategy_result = run_backtest_with_signals(
            bars_for_sim,
            signals_for_sim,
            initial_cash,
            commission_bps,
            decision_timeframe=timeframe,
        )
        benchmark_result = run_buy_and_hold_benchmark(
            bars_for_sim,
            initial_cash,
            commission_bps,
            decision_timeframe=timeframe,
        )

        metrics = compute_metrics(strategy_result, benchmark_result, initial_cash, timeframe)
        strategy_payload = serialize_simulation(strategy_result)
        benchmark_payload = serialize_simulation(benchmark_result)

        forecast_stats = compute_forecast_metrics(
            series,
            forecasts,
            start_index=sim_start,
            horizon=int(validated["forecast_horizon"]),
        )
        foundation_summary = {
            "model_type": model_type,
            "signal_counts": count_signals(signals_for_sim),
            "forecast_metrics": forecast_stats,
            "walk_forward": walk_forward_metadata(validated, len(bars)),
            **build_simulation_metadata(
                bars=bars,
                start_index=sim_start,
                decision_timeframe=timeframe,
            ),
            "forecast_samples": sparse_forecast_samples(
                bars,
                series,
                forecasts,
                timeframe=timeframe,
                stride=int(validated["forecast_sample_stride"]),
                start_index=sim_start,
            ),
        }

        final_params = {**validated, "foundation_summary": foundation_summary}
        await backtest_dal.finish_run(
            session,
            run["id"],
            status="completed",
            metrics=metrics,
            equity_curve=strategy_payload["equity_curve"],
            trades=strategy_payload["trades"],
            benchmark={
                "equity_curve": benchmark_payload["equity_curve"],
                "metrics": metrics,
            },
        )
        await _update_run_params(session, run["id"], final_params)
        await session.commit()

        return {
            **run,
            "strategy": model_type,
            "params": final_params,
            "status": "completed",
            "metrics": metrics,
            "equity_curve": strategy_payload["equity_curve"],
            "trades": strategy_payload["trades"],
            "benchmark": benchmark_payload,
            "foundation_summary": foundation_summary,
        }
    except Exception as exc:
        await backtest_dal.finish_run(
            session,
            run["id"],
            status="failed",
            error_message=str(exc),
        )
        await session.commit()
        raise


async def _update_run_params(session: AsyncSession, run_id: UUID, params: dict) -> None:
    from sqlalchemy import update

    from models.backtest import BacktestRun

    await session.execute(
        update(BacktestRun).where(BacktestRun.id == run_id).values(params=params),
    )


async def get_foundation_backtest_results(session: AsyncSession, run_id) -> dict | None:
    row = await backtest_dal.get_run(session, run_id)
    if not row:
        return None
    summary = (row.get("params") or {}).get("foundation_summary")
    if summary:
        row = {**row, "foundation_summary": summary}
    return row
