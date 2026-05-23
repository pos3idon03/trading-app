from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal, macro_dal
from features.backtesting.metrics import bars_per_year
from features.fred.catalog import SERIES_CATALOG
from features.ml.fundamentals_catalog import (
    DEFAULT_FUNDAMENTAL_METRICS,
    FUNDAMENTAL_METRIC_CODES_SET,
    SUPPORTED_PERIOD_TYPES,
)
from features.ml.hyperparameter_search import model_supports_hyperparameter_search

SUPPORTED_FEATURE_MODES = frozenset({"prices_only", "prices_macro", "prices_macro_fundamentals"})


def feature_mode_uses_macro(feature_mode: str) -> bool:
    return feature_mode in ("prices_macro", "prices_macro_fundamentals")


DEFAULT_MACRO_SERIES_IDS: list[str] = [
    series_id
    for series_id, meta in SERIES_CATALOG.items()
    if meta.get("category") in ("rates", "inflation")
]

DEFAULT_ML_PARAMS: dict[str, Any] = {
    "feature_mode": "prices_only",
    "macro_series_ids": DEFAULT_MACRO_SERIES_IDS,
    "macro_publication_lag_days": {},
    "fundamental_metrics": DEFAULT_FUNDAMENTAL_METRICS,
    "fundamental_period_type": "quarterly",
    "context_timeframes": [],
    "strategy_feature_ids": [],
    "strategy_feature_params": {},
    "label_mode": "binary",
    "label_threshold": 0.01,
    "label_method": "endpoint",
    "label_horizon": 5,
    "train_bars": 252,
    "test_bars": 63,
    "step_bars": 63,
    "buy_threshold": 0.55,
    "sell_threshold": 0.45,
    "random_forest_estimators": 100,
    "gradient_boosting_max_iter": 100,
}

ML_MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "ml_logistic": {
        "label": "Logistic Regression",
        "description": (
            "Walk-forward logistic regression on OHLCV-derived features. "
            "Predicts forward return direction; trades on out-of-sample windows only."
        ),
        "params": DEFAULT_ML_PARAMS,
        "constraints": {
            "label_horizon": (1, 60),
            "label_threshold": (0.001, 0.1),
            "train_bars": (30, 2000),
            "test_bars": (5, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
        },
    },
    "ml_random_forest": {
        "label": "Random Forest",
        "description": (
            "Walk-forward random forest classifier on OHLCV-derived features. "
            "Non-linear alternative to logistic regression."
        ),
        "params": DEFAULT_ML_PARAMS,
        "constraints": {
            "label_horizon": (1, 60),
            "label_threshold": (0.001, 0.1),
            "train_bars": (30, 2000),
            "test_bars": (5, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
            "random_forest_estimators": (10, 500),
        },
    },
    "ml_gradient_boosting": {
        "label": "Gradient Boosting",
        "description": (
            "Walk-forward histogram-based gradient boosting classifier. "
            "Strong non-linear model using sklearn HistGradientBoostingClassifier."
        ),
        "params": DEFAULT_ML_PARAMS,
        "constraints": {
            "label_horizon": (1, 60),
            "label_threshold": (0.001, 0.1),
            "train_bars": (30, 2000),
            "test_bars": (5, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
            "gradient_boosting_max_iter": (10, 500),
        },
    },
    "ml_xgboost": {
        "label": "XGBoost",
        "description": "Walk-forward XGBoost classifier for tabular trend prediction.",
        "params": DEFAULT_ML_PARAMS,
        "constraints": {
            "label_horizon": (1, 60),
            "label_threshold": (0.001, 0.1),
            "train_bars": (30, 2000),
            "test_bars": (5, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
            "xgboost_estimators": (10, 500),
            "xgboost_max_depth": (2, 16),
            "xgboost_learning_rate": (0.01, 0.5),
        },
    },
    "ml_knn": {
        "label": "K-Nearest Neighbors",
        "description": "Walk-forward KNN classifier using similar historical feature vectors.",
        "params": DEFAULT_ML_PARAMS,
        "constraints": {
            "label_horizon": (1, 60),
            "label_threshold": (0.001, 0.1),
            "train_bars": (30, 2000),
            "test_bars": (5, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
            "knn_neighbors": (1, 50),
        },
    },
}


def list_ml_models() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for model_id, meta in ML_MODEL_CATALOG.items():
        items.append(
            {
                "id": model_id,
                "label": meta["label"],
                "description": meta["description"],
                "params": meta["params"],
                "constraints": meta.get("constraints", {}),
                "supports_hyperparameter_search": model_supports_hyperparameter_search(model_id),
            }
        )
    return items


def resolve_ml_model(model_type: str) -> dict[str, Any]:
    if model_type not in ML_MODEL_CATALOG:
        raise ValueError(f"Unknown ML model type: {model_type}")
    return ML_MODEL_CATALOG[model_type]


def default_walk_forward_params(timeframe: str) -> dict[str, int]:
    bpy = bars_per_year(timeframe)
    train = max(30, min(2000, round(bpy)))
    test = max(5, min(500, round(bpy * 63 / 252)))
    step = test
    label_horizon = 5
    if timeframe == "1w":
        label_horizon = 4
    elif timeframe == "1mo":
        label_horizon = 3
    return {
        "train_bars": train,
        "test_bars": test,
        "step_bars": step,
        "label_horizon": label_horizon,
    }


def validate_ml_params(
    model_type: str,
    params: dict | None,
    timeframe: str = "1d",
) -> dict:
    meta = resolve_ml_model(model_type)
    tf_defaults = default_walk_forward_params(timeframe)
    merged = {**DEFAULT_ML_PARAMS, **tf_defaults, **(params or {})}
    constraints = meta.get("constraints", {})

    for key, bounds in constraints.items():
        if key not in merged:
            continue
        value = float(merged[key])
        low, high = bounds
        if value < low or value > high:
            raise ValueError(f"Parameter {key} must be between {low} and {high}")

    if float(merged["buy_threshold"]) <= float(merged["sell_threshold"]):
        raise ValueError("buy_threshold must be greater than sell_threshold")

    feature_mode = merged.get("feature_mode")
    if feature_mode not in SUPPORTED_FEATURE_MODES:
        supported = ", ".join(sorted(SUPPORTED_FEATURE_MODES))
        raise ValueError(f"Unsupported feature_mode: {feature_mode}. Supported: {supported}")

    if feature_mode in ("prices_macro", "prices_macro_fundamentals"):
        _validate_macro_series_ids(merged.get("macro_series_ids"))

    if feature_mode == "prices_macro_fundamentals":
        _validate_fundamental_metrics(merged.get("fundamental_metrics"))
        _validate_fundamental_period_type(merged.get("fundamental_period_type"))

    label_mode = str(merged.get("label_mode") or "binary")
    if label_mode not in ("binary", "ternary"):
        raise ValueError("label_mode must be 'binary' or 'ternary'")

    label_method = str(merged.get("label_method") or "endpoint")
    if label_method not in ("endpoint", "mean"):
        raise ValueError("label_method must be 'endpoint' or 'mean'")

    _validate_context_timeframes(merged.get("context_timeframes"), timeframe)
    _validate_strategy_feature_ids(merged.get("strategy_feature_ids"))

    return merged


def _validate_context_timeframes(raw: Any, decision_timeframe: str) -> None:
    if not raw:
        return
    if not isinstance(raw, list):
        raise ValueError("context_timeframes must be a list of timeframe strings")
    from features.backtesting.bar_loader import validate_timeframe

    for item in raw:
        validate_timeframe(str(item), "context timeframe")


def _validate_strategy_feature_ids(raw: Any) -> None:
    if not raw:
        return
    if not isinstance(raw, list):
        raise ValueError("strategy_feature_ids must be a list of strategy ids")
    from features.backtesting.strategies.registry import ENSEMBLE_LEG_STRATEGIES, STRATEGY_CATALOG

    for item in raw:
        sid = str(item)
        if sid not in STRATEGY_CATALOG:
            raise ValueError(f"Unknown strategy id: {sid}")
        if sid not in ENSEMBLE_LEG_STRATEGIES:
            raise ValueError(f"Strategy {sid} is not eligible as an ML feature")


def validate_inference_params(saved_model: dict, params: dict) -> dict:
    feature_mode = params.get("feature_mode")
    if feature_mode != saved_model.get("feature_mode"):
        raise ValueError(
            f"Inference feature_mode {feature_mode!r} does not match saved model "
            f"feature_mode {saved_model.get('feature_mode')!r}"
        )
    return params


def _validate_macro_series_ids(raw_ids: Any) -> None:
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("macro_series_ids must be a non-empty list when feature_mode is prices_macro")
    unknown = [sid for sid in raw_ids if sid not in SERIES_CATALOG]
    if unknown:
        raise ValueError(f"Unknown macro series ids: {', '.join(unknown)}")


def _validate_fundamental_metrics(raw_metrics: Any) -> None:
    if not isinstance(raw_metrics, list) or not raw_metrics:
        raise ValueError(
            "fundamental_metrics must be a non-empty list when feature_mode is prices_macro_fundamentals"
        )
    unknown = [code for code in raw_metrics if code not in FUNDAMENTAL_METRIC_CODES_SET]
    if unknown:
        raise ValueError(f"Unknown fundamental metric codes: {', '.join(unknown)}")


def _validate_fundamental_period_type(raw_period_type: Any) -> None:
    period_type = str(raw_period_type or "quarterly")
    if period_type not in SUPPORTED_PERIOD_TYPES:
        supported = ", ".join(sorted(SUPPORTED_PERIOD_TYPES))
        raise ValueError(
            f"Unsupported fundamental_period_type: {period_type}. Supported: {supported}"
        )


async def resolve_fundamental_metrics(
    session: AsyncSession,
    instrument_id: int,
    params: dict,
) -> tuple[list[str], list[str]]:
    requested = list(params.get("fundamental_metrics") or DEFAULT_FUNDAMENTAL_METRICS)
    _validate_fundamental_metrics(requested)
    period_type = str(params.get("fundamental_period_type") or "quarterly")

    resolved: list[str] = []
    warnings: list[str] = []
    for metric_code in requested:
        rows = await fundamentals_dal.list_fundamentals_for_symbol(
            session,
            instrument_id,
            period_type=period_type,
            metric_names=[metric_code],
            order="desc",
            limit=1,
        )
        if not rows:
            warnings.append(
                f"Fundamental metric {metric_code} has no ingested data; omitted."
            )
            continue
        resolved.append(metric_code)

    if len(resolved) < len(requested):
        warnings.append(
            "Fundamentals coverage is sparse for this symbol; backtest may reflect survivorship bias."
        )

    return resolved, warnings


async def resolve_macro_series_ids(
    session: AsyncSession,
    params: dict,
) -> tuple[list[str], list[str]]:
    requested = list(params.get("macro_series_ids") or DEFAULT_MACRO_SERIES_IDS)
    _validate_macro_series_ids(requested)

    resolved: list[str] = []
    warnings: list[str] = []
    for series_id in requested:
        latest = await macro_dal.get_latest_obs_date(session, series_id)
        if latest is None:
            warnings.append(f"Macro series {series_id} has no ingested observations; omitted.")
            continue
        resolved.append(series_id)
    return resolved, warnings


def minimum_bars_required(params: dict) -> int:
    from features.ml.price_features import FEATURE_WARMUP_BARS

    train = int(params["train_bars"])
    test = int(params["test_bars"])
    horizon = int(params["label_horizon"])
    return FEATURE_WARMUP_BARS + train + test + horizon
