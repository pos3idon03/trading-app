from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal
from features.backtesting.bar_context import MultiTimeframeContext
from features.backtesting.bar_loader import validate_timeframe
from features.ml.asof_join import bar_dates_from_bars
from features.ml.assembler import assemble_feature_matrix
from features.ml.catalog import resolve_fundamental_metrics, resolve_macro_series_ids, resolve_warmup_bars
from features.ml.context_features import build_context_feature_matrix
from features.ml.cross_sectional_factors import build_factor_features_at_index, factor_feature_names
from features.ml.fundamental_features import build_fundamental_feature_matrix
from features.ml.fundamental_loader import load_fundamental_observations
from features.ml import job_checkpoints
from features.ml.liquidity_features import (
    build_liquidity_feature_matrix,
    liquidity_series_requested,
)
from features.ml.macro_features import build_macro_feature_matrix
from features.ml.macro_loader import load_macro_observations
from features.ml.metadata_features import build_metadata_rows_for_bars
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
        macro_features_mode=str(validated_params.get("macro_features_mode") or "full"),
    )
    warnings = [*resolve_warnings, *build_warnings]
    if liquidity_series_requested(resolved_series_ids):
        liq_names, liq_rows, liq_warnings = build_liquidity_feature_matrix(
            bars,
            series_data,
            validated_params.get("macro_publication_lag_days"),
        )
        warnings.extend(liq_warnings)
        if liq_names:
            macro_names = [*macro_names, *liq_names]
            macro_rows = _merge_optional_rows(macro_rows, liq_rows)
    if not macro_names:
        raise ValueError("No macro feature columns could be built for the selected series")
    return macro_names, macro_rows, warnings, resolved_series_ids


def _merge_optional_rows(
    left: list,
    right: list,
) -> list:
    if not left:
        return right
    if not right:
        return left
    merged: list = []
    for left_row, right_row in zip(left, right):
        if left_row is None or right_row is None:
            merged.append(None)
            continue
        merged.append([*left_row, *right_row])
    return merged


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
        fundamental_features_mode=str(validated_params.get("fundamental_features_mode") or "full"),
        include_valuation_kpis=validated_params.get("feature_mode") == "prices_macro_fundamentals",
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


async def _build_news_features(
    session: AsyncSession,
    symbol: str,
    bars: list[dict],
    validated_params: dict,
) -> tuple[list[str], list, list[str]]:
    from config import get_settings
    from dal import news_sentiment_dal
    from features.ml.news_features import build_news_feature_matrix

    if not validated_params.get("include_news_sentiment"):
        return [], [], []

    settings = get_settings()
    if not settings.sentiment_enabled:
        return [], [], ["News sentiment is disabled (SENTIMENT_ENABLED=false)."]

    bar_start, bar_end = _bar_date_range(bars)
    daily_rows = await news_sentiment_dal.list_daily_sentiment_for_symbol(
        session,
        symbol=symbol,
        model_name=settings.sentiment_model_name,
        model_version=settings.sentiment_model_version,
        start=bar_start - timedelta(days=14),
        end=bar_end,
    )
    return build_news_feature_matrix(bars, daily_rows)


def _build_cross_sectional_block(
    returns_panel,
    symbol: str,
    bars: list[dict],
    validated_params: dict,
) -> tuple[list[str], list[Optional[list[float]]]]:
    if returns_panel is None or not validated_params.get("include_cross_sectional_factors"):
        return [], []

    sym = symbol.upper()
    if sym not in returns_panel.symbols:
        return [], []

    use_ica = bool(validated_params.get("cross_sectional_use_ica"))
    lookback = int(validated_params.get("cross_sectional_lookback_bars") or 63)
    names = factor_feature_names(use_ica=use_ica)
    date_to_panel_idx = {panel_date: idx for idx, panel_date in enumerate(returns_panel.dates)}

    rows: list[Optional[list[float]]] = []
    for bar_date in bar_dates_from_bars(bars):
        panel_idx = date_to_panel_idx.get(bar_date)
        if panel_idx is None:
            rows.append(None)
            continue
        factors = build_factor_features_at_index(
            returns_panel.log_returns,
            returns_panel.symbols,
            panel_idx,
            lookback=lookback,
            use_ica=use_ica,
        )
        sym_factors = factors.get(sym)
        if sym_factors is None or any(value is None for value in sym_factors):
            rows.append(None)
            continue
        rows.append([float(value) for value in sym_factors])
    return names, rows


def _merge_metadata_blocks(
    *blocks: tuple[list[str], list[Optional[list[float]]]],
) -> tuple[list[str], list[Optional[list[float]]]]:
    active = [(names, rows) for names, rows in blocks if names and rows]
    if not active:
        return [], []
    merged_names = [name for names, _rows in active for name in names]
    row_count = len(active[0][1])
    merged_rows: list[Optional[list[float]]] = []
    for row_index in range(row_count):
        combined: list[float] = []
        row_complete = True
        for _names, rows in active:
            row = rows[row_index]
            if row is None:
                row_complete = False
                break
            combined.extend(row)
        merged_rows.append(combined if row_complete else None)
    return merged_names, merged_rows


def _assemble_ml_features(
    feature_mode: str,
    *,
    price_names: list[str],
    price_rows: list,
    macro_names: list[str] | None = None,
    macro_rows: list | None = None,
    fund_names: list[str] | None = None,
    fund_rows: list | None = None,
    news_names: list[str] | None = None,
    news_rows: list | None = None,
    metadata_names: list[str] | None = None,
    metadata_rows: list | None = None,
    context_names: list[str] | None = None,
    context_rows: list | None = None,
    strategy_names: list[str] | None = None,
    strategy_rows: list | None = None,
) -> tuple[list[str], list]:
    return assemble_feature_matrix(
        feature_mode,
        price_names,
        price_rows,
        macro_names,
        macro_rows,
        fund_names,
        fund_rows,
        news_names=news_names,
        news_rows=news_rows,
        metadata_names=metadata_names,
        metadata_rows=metadata_rows,
        context_names=context_names,
        context_rows=context_rows,
        strategy_names=strategy_names,
        strategy_rows=strategy_rows,
    )


def _feature_build_result(
    feature_names: list[str],
    feature_rows: list,
    *,
    macro_warnings: list[str],
    fundamental_warnings: list[str],
    resolved_series_ids: list[str],
    resolved_fundamental_metrics: list[str],
    context_warnings: list[str],
    strategy_warnings: list[str],
) -> tuple[list[str], list, list[str], list[str], list[str], list[str], list[str], list[str]]:
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


async def _build_metadata_features(
    session: AsyncSession,
    *,
    symbol: str | None,
    bar_count: int,
    validated_params: dict,
    returns_panel=None,
    bars: list[dict],
) -> tuple[list[str], list[Optional[list[float]]]]:
    blocks: list[tuple[list[str], list[Optional[list[float]]]]] = []
    if validated_params.get("include_cross_sectional_factors") and symbol and returns_panel is not None:
        blocks.append(_build_cross_sectional_block(returns_panel, symbol, bars, validated_params))
    if validated_params.get("include_metadata_features") and symbol:
        instrument = await instrument_dal.get_by_symbol(session, symbol)
        if instrument:
            blocks.append(build_metadata_rows_for_bars(instrument, bar_count))
    return _merge_metadata_blocks(*blocks)


async def build_ml_feature_matrix(
    session: AsyncSession,
    bars: list[dict],
    validated_params: dict,
    *,
    instrument_id: int | None = None,
    symbol: str | None = None,
    decision_timeframe: str = "1d",
    bar_context: MultiTimeframeContext | None = None,
    returns_panel=None,
    job_id: UUID | None = None,
    progress_start: int = 0,
    progress_end: int = 100,
) -> tuple[list[str], list, list[str], list[str], list[str], list[str], list[str], list[str]]:
    feature_mode = validated_params["feature_mode"]
    macro_warnings: list[str] = []
    fundamental_warnings: list[str] = []
    context_warnings: list[str] = []
    strategy_warnings: list[str] = []
    resolved_series_ids: list[str] = []
    resolved_fundamental_metrics: list[str] = []

    await job_checkpoints.checkpoint_ml_job(session, job_id, progress_start)
    price_names, price_rows = await job_checkpoints.run_cpu_bound_step(
        session,
        job_id,
        build_price_feature_matrix,
        bars,
        denoise_method=str(validated_params.get("denoise_method") or "none"),
        warmup_bars=resolve_warmup_bars(validated_params),
    )
    await job_checkpoints.checkpoint_ml_job(
        session,
        job_id,
        job_checkpoints.progress_at_fraction(progress_start, progress_end, 0.4),
    )
    (
        context_names,
        context_rows,
        context_warnings,
        strategy_names,
        strategy_rows,
        strategy_warnings,
    ) = await job_checkpoints.run_cpu_bound_step(
        session,
        job_id,
        _build_optional_blocks,
        bars,
        validated_params,
        decision_timeframe,
        bar_context,
    )

    news_names: list[str] = []
    news_rows: list = []
    if symbol and validated_params.get("include_news_sentiment"):
        news_names, news_rows, news_warnings = await _build_news_features(
            session,
            symbol,
            bars,
            validated_params,
        )
        macro_warnings.extend(news_warnings)

    metadata_names, metadata_rows = await _build_metadata_features(
        session,
        symbol=symbol,
        bar_count=len(bars),
        validated_params=validated_params,
        returns_panel=returns_panel,
        bars=bars,
    )

    assemble_kwargs = {
        "price_names": price_names,
        "price_rows": price_rows,
        "news_names": news_names,
        "news_rows": news_rows,
        "metadata_names": metadata_names,
        "metadata_rows": metadata_rows,
        "context_names": context_names,
        "context_rows": context_rows,
        "strategy_names": strategy_names,
        "strategy_rows": strategy_rows,
    }

    if feature_mode == "prices_only":
        feature_names, feature_rows = _assemble_ml_features(feature_mode, **assemble_kwargs)
        return _feature_build_result(
            feature_names,
            feature_rows,
            macro_warnings=macro_warnings,
            fundamental_warnings=fundamental_warnings,
            resolved_series_ids=resolved_series_ids,
            resolved_fundamental_metrics=resolved_fundamental_metrics,
            context_warnings=context_warnings,
            strategy_warnings=strategy_warnings,
        )

    await job_checkpoints.checkpoint_ml_job(
        session,
        job_id,
        job_checkpoints.progress_at_fraction(progress_start, progress_end, 0.85),
    )
    macro_names, macro_rows, macro_feature_warnings, resolved_series_ids = await _build_macro_features(
        session,
        bars,
        validated_params,
    )
    macro_warnings.extend(macro_feature_warnings)

    if feature_mode == "prices_macro":
        feature_names, feature_rows = _assemble_ml_features(
            feature_mode,
            macro_names=macro_names,
            macro_rows=macro_rows,
            **assemble_kwargs,
        )
        return _feature_build_result(
            feature_names,
            feature_rows,
            macro_warnings=macro_warnings,
            fundamental_warnings=fundamental_warnings,
            resolved_series_ids=resolved_series_ids,
            resolved_fundamental_metrics=resolved_fundamental_metrics,
            context_warnings=context_warnings,
            strategy_warnings=strategy_warnings,
        )

    if instrument_id is None:
        raise ValueError("instrument_id is required for prices_macro_fundamentals feature mode")

    fund_names, fund_rows, fundamental_warnings, resolved_fundamental_metrics = (
        await _build_fundamental_features(session, instrument_id, bars, validated_params)
    )
    feature_names, feature_rows = _assemble_ml_features(
        feature_mode,
        macro_names=macro_names,
        macro_rows=macro_rows,
        fund_names=fund_names,
        fund_rows=fund_rows,
        **assemble_kwargs,
    )
    return _feature_build_result(
        feature_names,
        feature_rows,
        macro_warnings=macro_warnings,
        fundamental_warnings=fundamental_warnings,
        resolved_series_ids=resolved_series_ids,
        resolved_fundamental_metrics=resolved_fundamental_metrics,
        context_warnings=context_warnings,
        strategy_warnings=strategy_warnings,
    )


def collect_required_ml_timeframes(validated_params: dict, decision_timeframe: str) -> set[str]:
    timeframes = {decision_timeframe}
    for timeframe in _resolve_context_timeframes(validated_params, decision_timeframe):
        timeframes.add(timeframe)
    return timeframes
