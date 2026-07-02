"""Walk-forward PCA on fundamental KPI columns."""

from __future__ import annotations

from typing import Optional

from features.ml.block_pca import (
    BlockPcaState,
    fit_block_pca,
    transform_rows_with_block_pca,
)
from features.ml.fundamental_kpis import PE_RATIO_COLUMN
from features.ml.fundamentals_catalog import (
    DERIVED_FUNDAMENTAL_METRIC_CODES,
    RATIO_FUNDAMENTAL_METRICS,
)

SUPPORTED_FUNDAMENTAL_PCA_INPUT_MODES = frozenset({"kpi_only", "all_fundamental", "growth_only"})


def fundamental_pca_output_names(n_components: int) -> list[str]:
    return [f"pc_fund_{index + 1}" for index in range(n_components)]


def _metric_code_from_column(name: str) -> str | None:
    for suffix in ("_level", "_yoy", "_qoq", "_quarters_since_report"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    if name in DERIVED_FUNDAMENTAL_METRIC_CODES:
        return name
    return None


def _is_kpi_column(name: str, metric_codes: frozenset[str]) -> bool:
    if name == PE_RATIO_COLUMN:
        return True
    if name.endswith("_yoy") or name.endswith("_qoq"):
        code = _metric_code_from_column(name)
        return code is not None and code in metric_codes
    if name.endswith("_level"):
        code = _metric_code_from_column(name)
        return code is not None and code in RATIO_FUNDAMENTAL_METRICS
    return False


def _is_growth_column(name: str, metric_codes: frozenset[str]) -> bool:
    if name.endswith("_yoy") or name.endswith("_qoq"):
        code = _metric_code_from_column(name)
        return code is not None and code in metric_codes
    return False


def fundamental_column_indices(
    feature_names: list[str],
    *,
    fundamental_metrics: list[str],
    input_mode: str = "kpi_only",
) -> list[int]:
    if input_mode not in SUPPORTED_FUNDAMENTAL_PCA_INPUT_MODES:
        raise ValueError(
            "fundamental_pca_input_mode must be one of "
            f"{sorted(SUPPORTED_FUNDAMENTAL_PCA_INPUT_MODES)}",
        )

    metric_set = frozenset(fundamental_metrics)
    indices: list[int] = []
    for index, name in enumerate(feature_names):
        if input_mode == "all_fundamental":
            code = _metric_code_from_column(name)
            if code is not None and code in metric_set:
                indices.append(index)
            continue
        if input_mode == "growth_only":
            if _is_growth_column(name, metric_set):
                indices.append(index)
            continue
        if _is_kpi_column(name, metric_set):
            indices.append(index)
    return indices


def fit_fundamental_pca(
    x_train: list[list[float]],
    feature_names: list[str],
    params: dict,
) -> Optional[BlockPcaState]:
    if params.get("feature_mode") != "prices_macro_fundamentals":
        return None
    if not params.get("fundamental_pca_enabled"):
        return None

    metrics = [str(item) for item in (params.get("fundamental_metrics") or [])]
    input_mode = str(params.get("fundamental_pca_input_mode") or "kpi_only")
    indices = fundamental_column_indices(
        feature_names,
        fundamental_metrics=metrics,
        input_mode=input_mode,
    )
    fixed = params.get("fundamental_pca_n_components")
    halflife = params.get("fundamental_pca_ewm_halflife")
    return fit_block_pca(
        x_train,
        feature_names,
        indices,
        output_prefix="pc_fund",
        variance_threshold=float(params.get("fundamental_pca_variance_threshold", 0.85)),
        n_components=int(fixed) if fixed is not None else None,
        ewm_halflife=float(halflife) if halflife is not None else None,
    )


def transform_rows_with_fundamental_pca(
    rows: list[list[float]],
    state: BlockPcaState,
) -> list[list[float]]:
    return transform_rows_with_block_pca(rows, state)
