from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import backtest_dal, instrument_dal
from features.backtesting.bar_context import build_multi_timeframe_context
from features.backtesting.bar_loader import (
    collect_required_timeframes,
    load_multi_timeframe_bars,
    normalize_signal_timeframes,
    validate_timeframe,
)
from features.backtesting.signal_warmup import (
    collect_warmup_bars_by_timeframe,
    collect_warmup_bars_for_standalone,
    merge_warmup_maps,
)
from features.backtesting.engine import run_backtest, run_buy_and_hold_benchmark, serialize_simulation
from features.backtesting.metrics import compute_metrics
from features.backtesting.strategies.registry import (
    ensemble_min_bars,
    list_strategies,
    resolve_strategy,
    validate_params,
)


def get_strategy_catalog() -> list[dict]:
    return list_strategies()


async def run_backtest_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    strategy: str,
    params: dict | None,
    timeframe: str,
    signal_timeframe: str | None,
    start: datetime | None,
    end: datetime | None,
    initial_cash: float,
    commission_bps: float,
) -> dict:
    validate_timeframe(timeframe, "decision timeframe")
    if signal_timeframe is not None:
        validate_timeframe(signal_timeframe, "signal timeframe")

    validated_params = validate_params(strategy, params)
    validated_params, effective_signal_tf = normalize_signal_timeframes(
        strategy,
        validated_params,
        timeframe,
        signal_timeframe,
    )
    meta = resolve_strategy(strategy)

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    run = await backtest_dal.create_run(
        session,
        instrument_id=instrument["id"],
        symbol=instrument["symbol"],
        strategy=strategy,
        params=validated_params,
        timeframe=timeframe,
        start_date=start,
        end_date=end,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
    )
    await session.commit()

    try:
        required_timeframes = collect_required_timeframes(
            strategy,
            validated_params,
            timeframe,
            effective_signal_tf,
        )
        warmup_map = merge_warmup_maps(
            collect_warmup_bars_by_timeframe(strategy, validated_params, timeframe),
            collect_warmup_bars_for_standalone(
                strategy, validated_params, timeframe, effective_signal_tf,
            ),
        )
        bars_by_tf = await load_multi_timeframe_bars(
            session,
            instrument["id"],
            required_timeframes,
            start,
            end,
            decision_timeframe=timeframe,
            warmup_bars_by_tf=warmup_map,
        )
        decision_bars = bars_by_tf[timeframe]
        min_bars = ensemble_min_bars(validated_params) if strategy == "strategy_ensemble" else int(meta["min_bars"])
        if len(decision_bars) < min_bars:
            raise ValueError(
                f"Insufficient bars ({len(decision_bars)}) for strategy {strategy}. "
                f"Minimum required: {min_bars}"
            )

        _validate_signal_bar_counts(strategy, validated_params, bars_by_tf, timeframe, effective_signal_tf)

        bar_context = build_multi_timeframe_context(
            decision_timeframe=timeframe,
            decision_bars=decision_bars,
            bars_by_timeframe=bars_by_tf,
            standalone_signal_timeframe=effective_signal_tf,
        )

        strategy_result = run_backtest(
            decision_bars,
            strategy,
            validated_params,
            initial_cash,
            commission_bps,
            bar_context=bar_context,
            decision_timeframe=timeframe,
        )
        benchmark_result = run_buy_and_hold_benchmark(
            decision_bars,
            initial_cash,
            commission_bps,
            decision_timeframe=timeframe,
        )
        metrics = compute_metrics(strategy_result, benchmark_result, initial_cash, timeframe)
        strategy_payload = serialize_simulation(strategy_result)
        benchmark_payload = serialize_simulation(benchmark_result)

        await backtest_dal.finish_run(
            session,
            run["id"],
            status="completed",
            metrics=metrics,
            equity_curve=strategy_payload["equity_curve"],
            trades=strategy_payload["trades"],
            benchmark={"equity_curve": benchmark_payload["equity_curve"], "metrics": metrics},
        )
        await session.commit()

        return {
            **run,
            "status": "completed",
            "metrics": metrics,
            "equity_curve": strategy_payload["equity_curve"],
            "trades": strategy_payload["trades"],
            "benchmark": benchmark_payload,
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


def _validate_signal_bar_counts(
    strategy: str,
    params: dict,
    bars_by_tf: dict[str, list[dict]],
    decision_timeframe: str,
    signal_timeframe: str,
) -> None:
    if strategy == "strategy_ensemble":
        for leg in params["legs"]:
            leg_tf = leg["signal_timeframe"]
            min_bars = int(resolve_strategy(leg["strategy_id"])["min_bars"])
            if len(bars_by_tf[leg_tf]) < min_bars:
                raise ValueError(
                    f"Insufficient {leg_tf} bars for leg {leg['strategy_id']}. "
                    f"Minimum required: {min_bars}"
                )
        return

    min_bars = int(resolve_strategy(strategy)["min_bars"])
    bars = bars_by_tf[signal_timeframe]
    if len(bars) < min_bars:
        raise ValueError(
            f"Insufficient {signal_timeframe} bars for strategy {strategy}. "
            f"Minimum required: {min_bars}"
        )


async def get_backtest_results(session: AsyncSession, run_id: UUID) -> dict | None:
    return await backtest_dal.get_run(session, run_id)
