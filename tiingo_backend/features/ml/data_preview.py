from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from dal import macro_dal
from features.ml.catalog import feature_mode_uses_macro
from features.ml.feature_builder import collect_required_ml_timeframes
from features.ml.labels import build_labels, label_distribution
from features.ml.price_features import FEATURE_WARMUP_BARS


async def build_data_preview(
    session: AsyncSession,
    *,
    bars_by_timeframe: dict[str, list[dict]],
    decision_timeframe: str,
    validated_params: dict,
    macro_series_ids: list[str],
    fundamental_metrics: list[str],
    context_warnings: list[str],
    strategy_warnings: list[str],
) -> dict:
    bars = bars_by_timeframe[decision_timeframe]
    warnings: list[str] = [*context_warnings, *strategy_warnings]

    bar_counts = {timeframe: len(items) for timeframe, items in bars_by_timeframe.items()}
    required_tfs = collect_required_ml_timeframes(validated_params, decision_timeframe)
    for timeframe in required_tfs:
        if bar_counts.get(timeframe, 0) == 0:
            warnings.append(f"No bars loaded for timeframe {timeframe}.")

    macro_coverage = []
    if feature_mode_uses_macro(validated_params["feature_mode"]) and macro_series_ids:
        coverage_by_series = await macro_dal.get_release_date_coverage_batch(
            session,
            macro_series_ids,
        )
        for series_id in macro_series_ids:
            coverage = coverage_by_series.get(
                series_id,
                {"total": 0, "with_release_date": 0, "pct": 0.0},
            )
            macro_coverage.append({
                "series_id": series_id,
                "total_observations": coverage["total"],
                "with_release_date": coverage["with_release_date"],
                "release_date_pct": coverage["pct"],
            })
            if coverage["pct"] < 100:
                warnings.append(
                    f"Macro series {series_id} has {coverage['pct']}% ALFRED release_date coverage.",
                )

    labels = build_labels(
        bars,
        int(validated_params["label_horizon"]),
        label_mode=str(validated_params.get("label_mode") or "binary"),
        label_threshold=float(validated_params.get("label_threshold") or 0.01),
        label_method=str(validated_params.get("label_method") or "endpoint"),
    )
    distribution = label_distribution(labels)
    total_labeled = sum(distribution.values())
    if total_labeled:
        majority = max(distribution.values()) / total_labeled
        if majority > 0.85:
            warnings.append("Label distribution is highly imbalanced (>85% one class).")

    return {
        "decision_timeframe": decision_timeframe,
        "bar_counts": bar_counts,
        "warmup_bars_excluded": FEATURE_WARMUP_BARS,
        "macro_coverage": macro_coverage,
        "fundamental_metrics": fundamental_metrics,
        "context_timeframes": list(validated_params.get("context_timeframes") or []),
        "strategy_feature_ids": list(validated_params.get("strategy_feature_ids") or []),
        "label_preview": {
            "label_mode": validated_params.get("label_mode", "binary"),
            "label_horizon": validated_params["label_horizon"],
            "label_threshold": validated_params.get("label_threshold"),
            "class_distribution": distribution,
        },
        "warnings": warnings,
    }
