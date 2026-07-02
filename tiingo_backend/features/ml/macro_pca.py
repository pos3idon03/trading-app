"""Walk-forward PCA on macro feature columns grouped by FRED category."""

from __future__ import annotations

from dataclasses import dataclass

from features.fred.catalog import SERIES_CATALOG
from features.ml.block_pca import (
    BlockPcaState,
    block_pcas_output_names,
    fit_block_pca,
    transform_rows_with_block_pcas,
)
from features.ml.liquidity_features import liquidity_series_requested

SUPPORTED_MACRO_PCA_INPUT_MODES = frozenset({"changes_only", "all_macro"})

_MACRO_SUFFIXES = ("_level", "_chg_1m", "_chg_3m", "_days_since_update")
_LIQUIDITY_COLUMNS = frozenset(
    {
        "t10y2y_level",
        "t10y2y_chg_5d",
        "fed_net_liquidity",
        "fed_net_liquidity_roc_30d",
    },
)
_CHANGE_ONLY_COLUMNS = frozenset(
    {
        "t10y2y_chg_5d",
        "fed_net_liquidity_roc_30d",
    },
)


@dataclass
class MacroPcaBundle:
    feature_names: list[str]
    states: dict[str, BlockPcaState]
    output_names: list[str]


def _series_id_from_column(name: str, series_ids: frozenset[str]) -> str | None:
    for suffix in _MACRO_SUFFIXES:
        if not name.endswith(suffix):
            continue
        candidate = name[: -len(suffix)]
        if candidate in series_ids:
            return candidate
    return None


def _column_category(name: str, series_ids: frozenset[str]) -> str | None:
    if name in _LIQUIDITY_COLUMNS:
        return "liquidity"
    series_id = _series_id_from_column(name, series_ids)
    if series_id is None:
        return None
    return str(SERIES_CATALOG.get(series_id, {}).get("category") or "other")


def _include_column(name: str, input_mode: str) -> bool:
    if name.endswith("_days_since_update"):
        return False
    if input_mode == "all_macro":
        return True
    if name in _CHANGE_ONLY_COLUMNS:
        return True
    return name.endswith("_chg_1m") or name.endswith("_chg_3m")


def macro_columns_by_category(
    feature_names: list[str],
    macro_series_ids: list[str],
    *,
    input_mode: str = "changes_only",
) -> dict[str, list[int]]:
    if input_mode not in SUPPORTED_MACRO_PCA_INPUT_MODES:
        raise ValueError(
            "macro_pca_input_mode must be one of "
            f"{sorted(SUPPORTED_MACRO_PCA_INPUT_MODES)}",
        )

    series_set = frozenset(str(series_id) for series_id in macro_series_ids)
    include_liquidity = liquidity_series_requested(macro_series_ids)
    by_category: dict[str, list[int]] = {}

    for index, name in enumerate(feature_names):
        category = _column_category(name, series_set)
        if category is None:
            continue
        if category == "liquidity" and not include_liquidity:
            continue
        if _series_id_from_column(name, series_set) is None and name not in _LIQUIDITY_COLUMNS:
            continue
        if not _include_column(name, input_mode):
            continue
        by_category.setdefault(category, []).append(index)

    return by_category


def fit_macro_pca(
    x_train: list[list[float]],
    feature_names: list[str],
    params: dict,
) -> MacroPcaBundle | None:
    feature_mode = params.get("feature_mode")
    if feature_mode not in ("prices_macro", "prices_macro_fundamentals"):
        return None
    if not params.get("macro_pca_enabled"):
        return None

    series_ids = [str(item) for item in (params.get("macro_series_ids") or [])]
    input_mode = str(params.get("macro_pca_input_mode") or "changes_only")
    by_category = macro_columns_by_category(
        feature_names,
        series_ids,
        input_mode=input_mode,
    )

    fixed = params.get("macro_pca_n_components")
    halflife = params.get("macro_pca_ewm_halflife")
    variance = float(params.get("macro_pca_variance_threshold", 0.85))
    states: dict[str, BlockPcaState] = {}

    for category in sorted(by_category.keys()):
        indices = by_category[category]
        state = fit_block_pca(
            x_train,
            feature_names,
            indices,
            output_prefix=f"pc_macro_{category}",
            variance_threshold=variance,
            n_components=int(fixed) if fixed is not None else None,
            ewm_halflife=float(halflife) if halflife is not None else None,
        )
        if state is not None:
            states[category] = state

    if not states:
        return None

    ordered_states = [states[category] for category in sorted(states.keys())]
    return MacroPcaBundle(
        feature_names=list(feature_names),
        states=states,
        output_names=block_pcas_output_names(feature_names, ordered_states),
    )


def transform_rows_with_macro_pca(
    rows: list[list[float]],
    bundle: MacroPcaBundle,
) -> list[list[float]]:
    ordered_states = [bundle.states[category] for category in sorted(bundle.states.keys())]
    return transform_rows_with_block_pcas(rows, ordered_states)
