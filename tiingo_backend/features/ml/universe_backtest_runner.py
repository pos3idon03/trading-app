"""Multi-symbol ML backtest: per-symbol walk-forward + portfolio simulation."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import backtest_dal, instrument_dal
from features.backtesting.metrics import compute_metrics
from features.backtesting.portfolio_metrics import portfolio_to_simulation_result
from features.backtesting.portfolio_simulator import MultiAssetSimulationResult
from features.backtesting.simulator import SimulationResult
from features.backtesting.universe_loader import resolve_universe_symbols
from features.ml.job_checkpoints import checkpoint_ml_job
from features.ml.labels import build_labels, build_meta_label_targets
from features.backtesting.bar_loader import validate_timeframe
from features.ml.catalog import validate_ml_params
from features.ml.inference_holdout import (
    resolve_inference_bar_load_range,
    resolve_inference_eval_scope,
    resolve_inference_window,
)
from features.ml.universe_orchestrator import run_universe_ml_backtest
from features.ml.orchestrator import (
    _load_bars_and_features,
    _run_inference_backtest,
    _run_walk_forward_backtest,
    _update_run_params,
)


def _portfolio_to_simulation_result(
    portfolio: MultiAssetSimulationResult,
) -> SimulationResult:
    return portfolio_to_simulation_result(portfolio)


async def _signals_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    validated_params: dict,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    model_id: UUID | None,
    saved_model: dict | None,
    job_id: UUID | None,
    returns_panel=None,
) -> tuple[list[str], dict, list[dict], list[str]]:
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    (
        bars,
        feature_names,
        feature_rows,
        macro_warnings,
        fundamental_warnings,
        macro_series_ids,
        fundamental_metrics,
        _ctx,
        _strat,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
        job_id=job_id,
        returns_panel=returns_panel,
    )

    label_mode = str(validated_params.get("label_mode") or "binary")
    if label_mode == "meta_label":
        _mask, labels = build_meta_label_targets(bars, validated_params)
    else:
        labels = build_labels(
            bars,
            int(validated_params["label_horizon"]),
            label_mode=label_mode,
            label_threshold=float(validated_params.get("label_threshold") or 0.01),
            label_method=str(validated_params.get("label_method") or "endpoint"),
            params=validated_params,
        )

    if model_id and saved_model:
        eval_start, scope_meta = resolve_inference_window(
            train_metrics=saved_model.get("train_metrics"),
            hyperparams=saved_model.get("hyperparams") or validated_params,
            inference_eval_scope=resolve_inference_eval_scope(validated_params),
        )
        signals, ml_summary, _ = await _run_inference_backtest(
            session=session,
            model_id=model_id,
            validated_params=validated_params,
            feature_names=feature_names,
            feature_rows=feature_rows,
            labels=labels,
            bars=bars,
            macro_series_ids=macro_series_ids,
            macro_warnings=macro_warnings,
            fundamental_metrics=fundamental_metrics,
            fundamental_warnings=fundamental_warnings,
            eval_start_index=eval_start,
            evaluation_metadata=scope_meta,
        )
    else:
        signals, ml_summary, _ = await _run_walk_forward_backtest(
            model_type=model_type,
            validated_params=validated_params,
            feature_names=feature_names,
            feature_rows=feature_rows,
            labels=labels,
            bars=bars,
            macro_series_ids=macro_series_ids,
            macro_warnings=macro_warnings,
            fundamental_metrics=fundamental_metrics,
            fundamental_warnings=fundamental_warnings,
        )
    return signals, ml_summary, bars, feature_names


async def run_ml_universe_backtest(
    session: AsyncSession,
    *,
    primary_symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    initial_cash: float,
    commission_bps: float,
    symbols: list[str] | None,
    universe_id: int | None,
    job_id: UUID | None = None,
) -> dict:
    raw_params = dict(params or {})
    model_id_raw = raw_params.pop("model_id", None)
    model_id = UUID(str(model_id_raw)) if model_id_raw else None

    primary = await instrument_dal.get_by_symbol(session, primary_symbol)
    if not primary:
        raise LookupError(f"Instrument not found: {primary_symbol.upper()}")

    asset_type = str(primary.get("asset_type") or "equity")
    validated_params = validate_ml_params(
        model_type,
        raw_params,
        timeframe,
        asset_type=asset_type,
    )
    validate_timeframe(timeframe, "decision timeframe")

    as_of = start.date() if start else date.today()
    resolved, universe_warnings = await resolve_universe_symbols(
        session,
        universe_id=universe_id,
        symbols=symbols,
        as_of=as_of,
    )
    if primary_symbol.upper() not in resolved:
        resolved = [primary_symbol.upper(), *[s for s in resolved if s != primary_symbol.upper()]]

    saved_model: dict | None = None
    if model_id:
        from dal import ml_model_dal

        saved_model = await ml_model_dal.get_model(session, model_id)
        if not saved_model:
            raise ValueError(f"Saved model not found: {model_id}")
        start, end = resolve_inference_bar_load_range(
            train_metrics=saved_model.get("train_metrics"),
            request_start=start,
            request_end=end,
        )

    run = await backtest_dal.create_run(
        session,
        instrument_id=primary["id"],
        symbol=primary["symbol"],
        strategy=model_type,
        params={**validated_params, **({"model_id": str(model_id)} if model_id else {})},
        timeframe=timeframe,
        start_date=start,
        end_date=end,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
        universe_id=universe_id,
        symbol_list=resolved,
    )
    await session.commit()

    try:
        signals_by_symbol: dict[str, list[str]] = {}
        summaries: dict[str, dict] = {}
        await checkpoint_ml_job(session, job_id, 20)

        slippage_bps = float(validated_params.get("slippage_bps", 0.0))
        from features.backtesting.returns_panel import load_returns_panel

        panel = await load_returns_panel(
            session,
            symbols=resolved,
            timeframe=timeframe,
            start=start,
            end=end,
        )

        for idx, sym in enumerate(resolved):
            progress = 20 + int(60 * (idx + 1) / max(len(resolved), 1))
            await checkpoint_ml_job(session, job_id, progress)
            sig, summary, _bars, _names = await _signals_for_symbol(
                session,
                symbol=sym,
                model_type=model_type,
                validated_params=validated_params,
                timeframe=timeframe,
                start=start,
                end=end,
                model_id=model_id if sym == primary_symbol.upper() else None,
                saved_model=saved_model if sym == primary_symbol.upper() else None,
                job_id=None,
                returns_panel=panel if validated_params.get("include_cross_sectional_factors") else None,
            )
            signals_by_symbol[sym] = sig
            summaries[sym] = summary

        slippage_bps = float(validated_params.get("slippage_bps", 0.0))
        universe_result = await run_universe_ml_backtest(
            session,
            universe_id=universe_id,
            symbols=resolved,
            signals_by_symbol=signals_by_symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            initial_cash=initial_cash,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            sizing_params=validated_params,
        )

        portfolio = universe_result["simulation"]
        strategy_result = _portfolio_to_simulation_result(portfolio)
        benchmark_result = SimulationResult(
            equity_curve=strategy_result.equity_curve,
            trades=[],
            final_equity=initial_cash,
        )
        metrics = compute_metrics(
            strategy_result,
            benchmark_result,
            initial_cash,
            timeframe,
            asset_type=asset_type,
        )

        primary_summary = summaries.get(primary_symbol.upper(), {})
        ml_summary = {
            **primary_summary,
            "run_mode": "universe_portfolio",
            "symbols": universe_result["symbols"],
            "survivorship_warnings": universe_result["survivorship_warnings"],
            "target_weights": universe_result.get("target_weights"),
            "per_symbol_summaries": summaries,
            "universe_warnings": universe_warnings,
        }

        equity_payload = [
            {
                "date": p.date,
                "equity": p.equity,
                "cash": p.cash,
                "positions_value": p.positions_value,
                "drawdown_pct": p.drawdown_pct,
            }
            for p in portfolio.equity_curve
        ]
        trades_payload = [
            {
                "symbol": t.symbol,
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "qty": t.qty,
                "pnl": t.pnl,
                "return_pct": t.return_pct,
            }
            for t in portfolio.trades
        ]

        final_params = {**validated_params, "ml_summary": ml_summary}
        if model_id:
            final_params["model_id"] = str(model_id)

        await checkpoint_ml_job(session, job_id, 95)
        await backtest_dal.finish_run(
            session,
            run["id"],
            status="completed",
            metrics=metrics,
            equity_curve=equity_payload,
            trades=trades_payload,
            benchmark={"equity_curve": equity_payload, "metrics": metrics},
        )
        await _update_run_params(session, run["id"], final_params)
        await session.commit()

        return {
            **run,
            "strategy": model_type,
            "params": final_params,
            "status": "completed",
            "metrics": metrics,
            "equity_curve": equity_payload,
            "trades": trades_payload,
            "ml_summary": ml_summary,
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
