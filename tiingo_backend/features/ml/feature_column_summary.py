"""Group resolved ML feature column names for data-preview UI."""

from typing import Any

from features.ml.catalog import ALWAYS_INCLUDED_FEATURE_IDS
from features.ml.cross_sectional_factors import factor_feature_names
from features.ml.news_features import NEWS_FEATURE_NAMES
from features.ml.price_features import FEATURE_NAMES

_GROUP_ORDER = (
    "price",
    "volume",
    "macro",
    "fundamental",
    "news",
    "context",
    "strategy",
    "cross_sectional",
    "metadata",
    "other",
)

_GROUP_LABELS = {
    "price": "Price / technical",
    "volume": "Volume",
    "macro": "Macro (FRED)",
    "fundamental": "Fundamentals",
    "news": "News sentiment",
    "context": "Multi-timeframe context",
    "strategy": "Algo strategy",
    "cross_sectional": "Cross-sectional factors",
    "metadata": "Instrument metadata",
    "other": "Other",
}

_PRICE_TECHNICAL = frozenset(name for name in FEATURE_NAMES if name not in ALWAYS_INCLUDED_FEATURE_IDS)


def _macro_column_names(series_ids: list[str]) -> frozenset[str]:
    names: set[str] = set()
    for series_id in series_ids:
        names.add(f"{series_id}_level")
        names.add(f"{series_id}_chg_1m")
        names.add(f"{series_id}_chg_3m")
        names.add(f"{series_id}_days_since_update")
    names.update(
        {
            "t10y2y_level",
            "t10y2y_chg_5d",
            "fed_net_liquidity",
            "fed_net_liquidity_roc_30d",
        },
    )
    return frozenset(names)


def _fundamental_column_names(
    metric_codes: list[str],
    *,
    fundamental_features_mode: str = "full",
) -> frozenset[str]:
    from features.ml.fundamental_kpis import PE_RATIO_COLUMN

    names: set[str] = set()
    include_level = fundamental_features_mode != "growth_only"
    for code in metric_codes:
        if include_level:
            names.add(f"{code}_level")
        names.add(f"{code}_yoy")
        names.add(f"{code}_qoq")
        names.add(f"{code}_quarters_since_report")
    names.add(PE_RATIO_COLUMN)
    return frozenset(names)


def _classify_feature_name(
    name: str,
    *,
    macro_names: frozenset[str],
    fundamental_names: frozenset[str],
    cs_names: frozenset[str],
) -> str:
    if name in ALWAYS_INCLUDED_FEATURE_IDS:
        return "volume"
    if name in _PRICE_TECHNICAL or name.startswith("pc_tech_"):
        return "price"
    if name in macro_names or name.startswith("pc_macro_"):
        return "macro"
    if name in fundamental_names or name.startswith("pc_fund_"):
        return "fundamental"
    if name in NEWS_FEATURE_NAMES:
        return "news"
    if name.startswith("ctx_"):
        return "context"
    if name.startswith("strat_"):
        return "strategy"
    if name in cs_names:
        return "cross_sectional"
    if name.startswith("sector_") or name.startswith("industry_"):
        return "metadata"
    return "other"


def build_feature_groups(
    feature_names: list[str],
    validated_params: dict[str, Any],
    *,
    macro_series_ids: list[str] | None = None,
    fundamental_metrics: list[str] | None = None,
) -> dict[str, list[str]]:
    macro_ids = list(macro_series_ids or validated_params.get("macro_series_ids") or [])
    fund_metrics = list(
        fundamental_metrics or validated_params.get("fundamental_metrics") or [],
    )
    cs_names = frozenset(factor_feature_names(use_ica=False))

    macro_cols = _macro_column_names(macro_ids)
    fund_cols = _fundamental_column_names(
        fund_metrics,
        fundamental_features_mode=str(validated_params.get("fundamental_features_mode") or "full"),
    )

    buckets: dict[str, list[str]] = {key: [] for key in _GROUP_ORDER}
    for name in feature_names:
        group = _classify_feature_name(
            name,
            macro_names=macro_cols,
            fundamental_names=fund_cols,
            cs_names=cs_names,
        )
        buckets[group].append(name)

    return {key: buckets[key] for key in _GROUP_ORDER if buckets[key]}


def feature_group_labels() -> dict[str, str]:
    return dict(_GROUP_LABELS)
