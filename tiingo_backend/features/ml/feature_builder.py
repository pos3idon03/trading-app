from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from features.backtesting.bar_context import MultiTimeframeContext, build_multi_timeframe_context
from features.backtesting.bar_loader import validate_timeframe
from features.ml.assembler import assemble_feature_matrix
from features.ml.catalog import resolve_fundamental_metrics, resolve_macro_series_ids
from features.ml.context_features import build_context_feature_matrix
from features.ml.fundamental_features import build_fundamental_feature_matrix
from features.ml.fundamental_loader import load_fundamental_observations
from features.ml.macro_features import build_macro_feature_matrix
from features.ml.macro_loader import load_macro_observations
from features.ml.price_features import build_price_feature_matrix
from features.ml.strategy_features import build_strategy_feature_matrix


def _bar_date_range(bars: list[dict]) -> tuple[date, date]:
    from features.ml.asof_join import bar_dates_from_bars

    dates = bar_dates_from_bars(bars)
    return dates[0], dates[-1]


def _resolve_context_timeframes(validated_params: dict, decision_timeframe: str) -> list[str]:
    raw = validated_params.get("context_timeframes") or []
    if not isinstance(raw, list):
        return []
    resolved: list[str] = []
    for timeframe in raw:
        tf = str(timeframe)
        validate_timeframe(tf, "context timeframe")
        if tf != decision_timeframe and tf not in resolved:
            resolved.append(tf)
    return resolved


def _resolve_strategy_ids(validated_params: dict) -> list[str]:
    raw = validated_params.get("strategy_feature_ids") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


async def _build_macro_features(
    session: AsyncSession,
    bars: list[dict],
    validated_params: dict,
) -> tuple[list[str], list, list[str], list[str]]:
    resolved_series_ids, resolve_warnings = await resolve_macro_series_ids(session, validated_params)
    if not resolved_series_ids:
        raise ValueError("No ingested macro series available for prices_macro feature mode")

    bar_start, bar_end = _bar_date_range(bars)
    series_data = await load_macro_observations(session, resolved_series_ids, bar_start, bar_end)
    macro_names, macro_rows, build_warnings = build_macro_feature_matrix(
        bars,
        series_data,
        resolved_series_ids,
        validated_params.get("macro_publication_lag_days"),
    )
    warnings = [*resolve_warnings, *build_warnings]
    if not macro_names:
        raise ValueError("No macro feature columns could be built for the selected series")
    return macro_names, macro_rows, warnings, resolved_series_ids


async def _build_fundamental_features(
    session: AsyncSession,
    instrument_id: int,
    bars: list[dict],
    validated_params: dict,
) -> tuple[list[str], list, list[str], list[str]]:
    resolved_metrics, resolve_warnings = await resolve_fundamental_metrics(
        session,
        instrument_id,
        validated_params,
    )
    if not resolved_metrics:
        raise ValueError("No ingested fundamental metrics available for prices_macro_fundamentals mode")

    period_type = str(validated_params.get("fundamental_period_type") or "quarterly")
    bar_start, bar_end = _bar_date_range(bars)
    metric_data = await load_fundamental_observations(
        session,
        instrument_id,
        resolved_metrics,
        period_type,
        bar_start,
        bar_end,
    )
    fund_names, fund_rows, build_warnings = build_fundamental_feature_matrix(
        bars,
        metric_data,
        resolved_metrics,
        period_type,
    )
    warnings = [*resolve_warnings, *build_warnings]
    if not fund_names:
        raise ValueError("No fundamental feature columns could be built for the selected metrics")
    return fund_names, fund_rows, warnings, resolved_metrics


def _build_optional_blocks(
    bars: list[dict],
    validated_params: dict,
    decision_timeframe: str,
    bar_context: MultiTimeframeContext | None,
) -> tuple[list[str], list, list[str], list[str], list, list[str]]:
    context_names: list[str] = []
    context_rows: list = []
    context_warnings: list[str] = []
    strategy_names: list[str] = []
    strategy_rows: list = []
    strategy_warnings: list[str] = []

    context_tfs = _resolve_context_timeframes(validated_params, decision_timeframe)
    if context_tfs and bar_context is not None:
        context_names, context_rows, context_warnings = build_context_feature_matrix(
            bar_context,
            context_tfs,
        )

    strategy_ids = _resolve_strategy_ids(validated_params)
    if strategy_ids:
        params_map = validated_params.get("strategy_feature_params") or {}
        strategy_names, strategy_rows, strategy_warnings = build_strategy_feature_matrix(
            bars,
            strategy_ids,
            params_map if isinstance(params_map, dict) else {},
        )

    return (
        context_names,
        context_rows,
        context_warnings,
        strategy_names,
        strategy_rows,
        strategy_warnings,
    )


async def build_ml_feature_matrix(
    session: AsyncSession,
    bars: list[dict],
    validated_params: dict,
    *,
    instrument_id: int | None = None,
    decision_timeframe: str = "1d",
    bar_context: MultiTimeframeContext | None = None,
) -> tuple[list[str], list, list[str], list[str], list[str], list[str], list[str], list[str]]:
    price_names, price_rows = build_price_feature_matrix(bars)
    feature_mode = validated_params["feature_mode"]
    macro_warnings: list[str] = []
    fundamental_warnings: list[str] = []
    context_warnings: list[str] = []
    strategy_warnings: list[str] = []
    resolved_series_ids: list[str] = []
    resolved_fundamental_metrics: list[str] = []

    (
        context_names,
        context_rows,
        context_warnings,
        strategy_names,
        strategy_rows,
        strategy_warnings,
    ) = _build_optional_blocks(bars, validated_params, decision_timeframe, bar_context)

    if feature_mode == "prices_only":
        feature_names, feature_rows = assemble_feature_matrix(
            feature_mode,
            price_names,
            price_rows,
            context_names=context_names,
            context_rows=context_rows,
            strategy_names=strategy_names,
            strategy_rows=strategy_rows,
        )
        return (
            feature_names,
            feature_rows,
            macro_warnings,
            fundamental_warnings,
            resolved_series_ids,
            resolved_fundamental_metrics,
            context_warnings,
            strategy_warnings,
        )

    macro_names, macro_rows, macro_warnings, resolved_series_ids = await _build_macro_features(
        session,
        bars,
        validated_params,
    )

    if feature_mode == "prices_macro":
        feature_names, feature_rows = assemble_feature_matrix(
            feature_mode,
            price_names,
            price_rows,
            macro_names,
            macro_rows,
            context_names=context_names,
            context_rows=context_rows,
            strategy_names=strategy_names,
            strategy_rows=strategy_rows,
        )
        return (
            feature_names,
            feature_rows,
            macro_warnings,
            fundamental_warnings,
            resolved_series_ids,
            resolved_fundamental_metrics,
            context_warnings,
            strategy_warnings,
        )

    if instrument_id is None:
        raise ValueError("instrument_id is required for prices_macro_fundamentals feature mode")

    fund_names, fund_rows, fundamental_warnings, resolved_fundamental_metrics = (
        await _build_fundamental_features(session, instrument_id, bars, validated_params)
    )
    feature_names, feature_rows = assemble_feature_matrix(
        feature_mode,
        price_names,
        price_rows,
        macro_names,
        macro_rows,
        fund_names,
        fund_rows,
        context_names=context_names,
        context_rows=context_rows,
        strategy_names=strategy_names,
        strategy_rows=strategy_rows,
    )
    return (
        feature_names,
        feature_rows,
        macro_warnings,
        fundamental_warnings,
        resolved_series_ids,
        resolved_fundamental_metrics,
        context_warnings,
        strategy_warnings,
    )


def collect_required_ml_timeframes(validated_params: dict, decision_timeframe: str) -> set[str]:
    timeframes = {decision_timeframe}
    for timeframe in _resolve_context_timeframes(validated_params, decision_timeframe):
        timeframes.add(timeframe)
    return timeframes
