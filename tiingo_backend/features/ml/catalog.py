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
from features.backtesting.trade_exits import (
    SUPPORTED_EXIT_POLICIES,
    default_exit_policy_for_label_mode,
)
from features.ml.hyperparameter_search import model_supports_hyperparameter_search

SUPPORTED_FEATURE_MODES = frozenset({"prices_only", "prices_macro", "prices_macro_fundamentals"})

ALWAYS_INCLUDED_FEATURE_IDS: list[str] = ["volume_rel_20"]


def feature_mode_uses_macro(feature_mode: str) -> bool:
    return feature_mode in ("prices_macro", "prices_macro_fundamentals")


DEFAULT_MACRO_SERIES_IDS: list[str] = [
    series_id
    for series_id, meta in SERIES_CATALOG.items()
    if meta.get("category") in ("rates", "inflation")
]

CRYPTO_MACRO_SERIES_IDS = ["T10Y2Y", "WALCL", "WTREGEN"]

CRYPTO_ML_PRESET: dict[str, Any] = {
    "feature_mode": "prices_macro",
    "macro_series_ids": CRYPTO_MACRO_SERIES_IDS,
    "macro_publication_lag_days": {"rates": 1},
    "include_news_sentiment": True,
    "strategy_feature_ids": [],
    "label_mode": "meta_label",
    "base_strategy_id": "crypto_trend_entry",
    "base_strategy_params": {"slow_period": 50, "rsi_period": 14, "rsi_max": 65.0},
    "profit_atr_mult": 2.0,
    "stop_atr_mult": 1.5,
    "max_horizon_bars": 48,
    "meta_gate_threshold": 0.65,
    "commission_bps": 20.0,
    "slippage_bps": 5.0,
    "buy_threshold": 0.65,
    "sell_threshold": 0.35,
}

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
    "warmup_bars": 200,
    "train_bars": 252,
    "test_bars": 63,
    "step_bars": 63,
    "buy_threshold": 0.55,
    "sell_threshold": 0.45,
    "inference_eval_scope": "holdout",
    "include_news_sentiment": False,
    "slippage_bps": 0.0,
    "base_strategy_id": "crypto_trend_entry",
    "base_strategy_params": {},
    "profit_atr_mult": 2.0,
    "stop_atr_mult": 1.5,
    "max_horizon_bars": 48,
    "meta_gate_threshold": 0.65,
    "meta_label_min_train_events": 4,
    "random_forest_estimators": 100,
    "gradient_boosting_max_iter": 100,
    "denoise_method": "none",
    "include_cross_sectional_factors": False,
    "include_metadata_features": False,
    "dynamic_indicator_selection": False,
    "indicator_groups": ["momentum", "mean_reversion", "volatility"],
    "sizing_method": "fixed_fraction",
    "kelly_fraction": 0.25,
    "hrp_lookback_bars": 252,
    "rebalance_frequency": 21,
    "hrp_linkage_method": "single",
    "lstm_seq_length": 32,
    "lstm_hidden_size": 64,
    "lstm_num_layers": 2,
    "lstm_epochs": 10,
    "lstm_dropout": 0.2,
    "lstm_learning_rate": 0.001,
    "lstm_batch_size": 32,
    "correlation_prune_threshold": 0.75,
    "use_smote": True,
    "atr_period": 14,
    "technical_pca_enabled": True,
    "technical_pca_variance_threshold": 0.85,
    "technical_pca_n_components": None,
    "technical_pca_ewm_halflife": None,
    "macro_features_mode": "changes_only",
    "macro_pca_enabled": True,
    "macro_pca_variance_threshold": 0.85,
    "macro_pca_n_components": None,
    "macro_pca_ewm_halflife": None,
    "macro_pca_input_mode": "changes_only",
    "fundamental_features_mode": "growth_only",
    "fundamental_pca_enabled": True,
    "fundamental_pca_variance_threshold": 0.85,
    "fundamental_pca_n_components": None,
    "fundamental_pca_ewm_halflife": None,
    "fundamental_pca_input_mode": "kpi_only",
    "lstm_early_stopping_patience": 3,
    "lstm_validation_fraction": 0.15,
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
            "train_bars": (10, 2000),
            "test_bars": (1, 500),
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
            "train_bars": (10, 2000),
            "test_bars": (1, 500),
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
            "train_bars": (10, 2000),
            "test_bars": (1, 500),
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
            "train_bars": (10, 2000),
            "test_bars": (1, 500),
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
            "train_bars": (10, 2000),
            "test_bars": (1, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
            "knn_neighbors": (1, 50),
        },
    },
    "ml_lstm": {
        "label": "Stacked LSTM",
        "description": (
            "Walk-forward stacked LSTM on sequence windows of tabular features. "
            "Captures temporal dependencies in financial time series."
        ),
        "params": DEFAULT_ML_PARAMS,
        "constraints": {
            "label_horizon": (1, 60),
            "label_threshold": (0.001, 0.1),
            "train_bars": (10, 2000),
            "test_bars": (1, 500),
            "step_bars": (1, 500),
            "buy_threshold": (0.51, 0.99),
            "sell_threshold": (0.01, 0.49),
            "lstm_seq_length": (8, 128),
            "lstm_hidden_size": (16, 256),
            "lstm_num_layers": (1, 4),
            "lstm_epochs": (1, 100),
            "lstm_dropout": (0.0, 0.5),
            "lstm_learning_rate": (0.0001, 0.01),
        },
    },
}

SUPPORTED_LABEL_MODES = frozenset({"binary", "ternary", "meta_label"})

DEFAULT_LABEL_MODE_BY_MODEL: dict[str, str] = {
    "ml_logistic": "binary",
    "ml_random_forest": "ternary",
    "ml_gradient_boosting": "binary",
    "ml_xgboost": "binary",
    "ml_knn": "binary",
    "ml_lstm": "meta_label",
}


def default_label_mode_for_model(model_type: str) -> str:
    return DEFAULT_LABEL_MODE_BY_MODEL.get(model_type, "binary")


def validate_model_label_search_configs(
    configs: list[dict[str, str]] | None,
) -> list[tuple[str, str]]:
    if not configs:
        return []
    resolved: list[tuple[str, str]] = []
    for entry in configs:
        model_type = str(entry.get("model_type") or "").strip()
        label_mode = str(entry.get("label_mode") or "binary").strip()
        if not model_type:
            raise ValueError("model_configs entries require model_type")
        resolve_ml_model(model_type)
        if label_mode not in SUPPORTED_LABEL_MODES:
            raise ValueError(
                "label_mode must be 'binary', 'ternary', or 'meta_label'",
            )
        resolved.append((model_type, label_mode))
    return resolved


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


def get_crypto_ml_preset(timeframe: str = "1h") -> dict[str, Any]:
    wfo = default_walk_forward_params(timeframe, asset_type="crypto")
    return {**DEFAULT_ML_PARAMS, **CRYPTO_ML_PRESET, **wfo}


LABEL_SEARCH_HORIZON_OFFSETS = (-4, -2, 0, 2, 4)


def label_search_horizons(
    center: int,
    *,
    min_horizon: int = 1,
    max_horizon: int = 60,
) -> list[int]:
    values = sorted({
        center + offset
        for offset in LABEL_SEARCH_HORIZON_OFFSETS
        if min_horizon <= center + offset <= max_horizon
    })
    return values


def default_walk_forward_params(
    timeframe: str,
    *,
    asset_type: str = "equity",
) -> dict[str, int]:
    bpy = bars_per_year(timeframe, asset_type=asset_type)
    if asset_type == "crypto" and timeframe == "1h":
        train = max(10, min(2000, round(bpy / 2)))
        test = max(1, min(500, round(bpy / 12)))
        step = test
        label_horizon = 5
        return {
            "train_bars": train,
            "test_bars": test,
            "step_bars": step,
            "label_horizon": label_horizon,
        }

    train = max(10, min(2000, round(bpy)))
    test = max(1, min(500, round(bpy * 63 / 252)))
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
    *,
    asset_type: str = "equity",
) -> dict:
    meta = resolve_ml_model(model_type)
    tf_defaults = default_walk_forward_params(timeframe, asset_type=asset_type)
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
    if label_mode not in ("binary", "ternary", "meta_label"):
        raise ValueError("label_mode must be 'binary', 'ternary', or 'meta_label'")

    if label_mode == "meta_label":
        _validate_meta_label_params(merged)

    label_method = str(merged.get("label_method") or "endpoint")
    if label_method not in ("endpoint", "mean"):
        raise ValueError("label_method must be 'endpoint' or 'mean'")

    denoise = str(merged.get("denoise_method") or "none")
    if denoise not in ("none", "kalman", "wavelet"):
        raise ValueError("denoise_method must be 'none', 'kalman', or 'wavelet'")

    sizing = str(merged.get("sizing_method") or "fixed_fraction")
    if sizing not in ("fixed_fraction", "kelly", "hrp"):
        raise ValueError("sizing_method must be 'fixed_fraction', 'kelly', or 'hrp'")

    _validate_context_timeframes(merged.get("context_timeframes"), timeframe)
    _validate_strategy_feature_ids(merged.get("strategy_feature_ids"))
    _validate_inference_eval_scope(merged.get("inference_eval_scope"))

    threshold = float(merged.get("correlation_prune_threshold", 0.75))
    if threshold < 0 or threshold > 1:
        raise ValueError("correlation_prune_threshold must be between 0 and 1")

    macro_mode = str(merged.get("macro_features_mode") or "full")
    if macro_mode not in ("full", "changes_only"):
        raise ValueError("macro_features_mode must be 'full' or 'changes_only'")
    merged["macro_features_mode"] = macro_mode

    if merged.get("macro_pca_enabled") is not None:
        merged["macro_pca_enabled"] = bool(merged["macro_pca_enabled"])
    macro_variance = float(merged.get("macro_pca_variance_threshold", 0.85))
    if macro_variance <= 0 or macro_variance > 1:
        raise ValueError("macro_pca_variance_threshold must be between 0 and 1")
    merged["macro_pca_variance_threshold"] = macro_variance

    macro_fixed = merged.get("macro_pca_n_components")
    if macro_fixed is not None:
        macro_fixed = int(macro_fixed)
        if macro_fixed < 1 or macro_fixed > 50:
            raise ValueError("macro_pca_n_components must be between 1 and 50")
        merged["macro_pca_n_components"] = macro_fixed

    macro_halflife = merged.get("macro_pca_ewm_halflife")
    if macro_halflife is not None:
        macro_halflife = float(macro_halflife)
        if macro_halflife <= 0:
            raise ValueError("macro_pca_ewm_halflife must be positive when set")
        merged["macro_pca_ewm_halflife"] = macro_halflife

    macro_input = str(merged.get("macro_pca_input_mode") or "changes_only")
    from features.ml.macro_pca import SUPPORTED_MACRO_PCA_INPUT_MODES
    if macro_input not in SUPPORTED_MACRO_PCA_INPUT_MODES:
        supported = ", ".join(sorted(SUPPORTED_MACRO_PCA_INPUT_MODES))
        raise ValueError(f"macro_pca_input_mode must be one of: {supported}")
    merged["macro_pca_input_mode"] = macro_input

    if merged.get("technical_pca_enabled") is not None:
        merged["technical_pca_enabled"] = bool(merged["technical_pca_enabled"])
    variance_threshold = float(merged.get("technical_pca_variance_threshold", 0.85))
    if variance_threshold <= 0 or variance_threshold > 1:
        raise ValueError("technical_pca_variance_threshold must be between 0 and 1")
    merged["technical_pca_variance_threshold"] = variance_threshold

    fixed_components = merged.get("technical_pca_n_components")
    if fixed_components is not None:
        fixed_components = int(fixed_components)
        if fixed_components < 1 or fixed_components > 50:
            raise ValueError("technical_pca_n_components must be between 1 and 50")
        merged["technical_pca_n_components"] = fixed_components

    halflife = merged.get("technical_pca_ewm_halflife")
    if halflife is not None:
        halflife = float(halflife)
        if halflife <= 0:
            raise ValueError("technical_pca_ewm_halflife must be positive when set")
        merged["technical_pca_ewm_halflife"] = halflife

    patience = int(merged.get("lstm_early_stopping_patience", 3))
    if patience < 1 or patience > 20:
        raise ValueError("lstm_early_stopping_patience must be between 1 and 20")
    merged["lstm_early_stopping_patience"] = patience

    validation_fraction = float(merged.get("lstm_validation_fraction", 0.15))
    if validation_fraction <= 0 or validation_fraction >= 0.5:
        raise ValueError("lstm_validation_fraction must be between 0 and 0.5")
    merged["lstm_validation_fraction"] = validation_fraction


    fund_mode = str(merged.get("fundamental_features_mode") or "full")
    if fund_mode not in ("full", "growth_only"):
        raise ValueError("fundamental_features_mode must be 'full' or 'growth_only'")
    merged["fundamental_features_mode"] = fund_mode

    if merged.get("fundamental_pca_enabled") is not None:
        merged["fundamental_pca_enabled"] = bool(merged["fundamental_pca_enabled"])
    fund_variance = float(merged.get("fundamental_pca_variance_threshold", 0.85))
    if fund_variance <= 0 or fund_variance > 1:
        raise ValueError("fundamental_pca_variance_threshold must be between 0 and 1")
    merged["fundamental_pca_variance_threshold"] = fund_variance

    fund_fixed = merged.get("fundamental_pca_n_components")
    if fund_fixed is not None:
        fund_fixed = int(fund_fixed)
        if fund_fixed < 1 or fund_fixed > 50:
            raise ValueError("fundamental_pca_n_components must be between 1 and 50")
        merged["fundamental_pca_n_components"] = fund_fixed

    fund_halflife = merged.get("fundamental_pca_ewm_halflife")
    if fund_halflife is not None:
        fund_halflife = float(fund_halflife)
        if fund_halflife <= 0:
            raise ValueError("fundamental_pca_ewm_halflife must be positive when set")
        merged["fundamental_pca_ewm_halflife"] = fund_halflife

    fund_input = str(merged.get("fundamental_pca_input_mode") or "kpi_only")
    from features.ml.fundamental_pca import SUPPORTED_FUNDAMENTAL_PCA_INPUT_MODES
    if fund_input not in SUPPORTED_FUNDAMENTAL_PCA_INPUT_MODES:
        supported = ", ".join(sorted(SUPPORTED_FUNDAMENTAL_PCA_INPUT_MODES))
        raise ValueError(f"fundamental_pca_input_mode must be one of: {supported}")
    merged["fundamental_pca_input_mode"] = fund_input

    _validate_warmup_bars(merged)
    _validate_indicator_groups(merged)
    _apply_exit_policy_defaults(merged)

    return merged


def _validate_indicator_groups(merged: dict) -> None:
    from features.ml.regime_features import (
        DEFAULT_INDICATOR_GROUPS,
        resolve_enabled_indicator_groups,
    )

    raw = merged.get("indicator_groups")
    if raw is None:
        merged["indicator_groups"] = list(DEFAULT_INDICATOR_GROUPS)
        return
    if not isinstance(raw, list):
        raise ValueError("indicator_groups must be a list of group names")
    merged["indicator_groups"] = list(resolve_enabled_indicator_groups(merged))
    if merged.get("dynamic_indicator_selection") and not merged["indicator_groups"]:
        raise ValueError(
            "indicator_groups must be non-empty when dynamic_indicator_selection is enabled",
        )


def _validate_warmup_bars(merged: dict) -> None:
    warmup = int(merged.get("warmup_bars", 200))
    if warmup < 50 or warmup > 500:
        raise ValueError("warmup_bars must be between 50 and 500")
    merged["warmup_bars"] = warmup
    train = int(merged["train_bars"])
    if train <= warmup:
        raise ValueError(
            f"train_bars ({train}) must be greater than warmup_bars ({warmup})",
        )


def _apply_exit_policy_defaults(merged: dict) -> None:
    label_mode = str(merged.get("label_mode") or "binary")
    policy = str(merged.get("exit_policy") or "").strip()
    if not policy:
        merged["exit_policy"] = default_exit_policy_for_label_mode(label_mode)
    elif policy not in SUPPORTED_EXIT_POLICIES:
        raise ValueError(
            f"exit_policy must be one of {sorted(SUPPORTED_EXIT_POLICIES)}",
        )

    atr_period = int(merged.get("atr_period", 14))
    if atr_period < 1 or atr_period > 60:
        raise ValueError("atr_period must be between 1 and 60")
    merged["atr_period"] = atr_period

    if merged.get("max_hold_bars") is not None:
        max_hold = int(merged["max_hold_bars"])
        if max_hold < 1 or max_hold > 500:
            raise ValueError("max_hold_bars must be between 1 and 500")
        merged["max_hold_bars"] = max_hold


def _validate_meta_label_params(params: dict) -> None:
    threshold = float(params.get("meta_gate_threshold", 0.65))
    if threshold < 0.51 or threshold > 0.99:
        raise ValueError("meta_gate_threshold must be between 0.51 and 0.99")
    max_horizon = int(params.get("max_horizon_bars", 48))
    if max_horizon < 1 or max_horizon > 500:
        raise ValueError("max_horizon_bars must be between 1 and 500")
    from features.backtesting.strategies.registry import STRATEGY_CATALOG

    base_id = str(params.get("base_strategy_id") or "crypto_trend_entry")
    if base_id not in STRATEGY_CATALOG:
        raise ValueError(f"Unknown base_strategy_id: {base_id}")


def _validate_inference_eval_scope(raw: Any) -> None:
    from features.ml.inference_holdout import SUPPORTED_INFERENCE_EVAL_SCOPES

    scope = str(raw or "holdout")
    if scope not in SUPPORTED_INFERENCE_EVAL_SCOPES:
        supported = ", ".join(sorted(SUPPORTED_INFERENCE_EVAL_SCOPES))
        raise ValueError(f"inference_eval_scope must be one of: {supported}")


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


def resolve_warmup_bars(params: dict) -> int:
    return int(params.get("warmup_bars", 200))


def minimum_bars_required(params: dict) -> int:
    train = int(params["train_bars"])
    test = int(params["test_bars"])
    label_mode = str(params.get("label_mode") or "binary")
    if label_mode == "meta_label":
        horizon = int(params.get("max_horizon_bars", 48))
    else:
        horizon = int(params["label_horizon"])
    return resolve_warmup_bars(params) + train + test + horizon


def minimum_bars_for_inference(params: dict) -> int:
    """Bars needed to compute features for one live prediction (not full walk-forward)."""
    from features.backtesting.strategies.registry import STRATEGY_CATALOG

    minimum = resolve_warmup_bars(params)
    for strategy_id in params.get("strategy_feature_ids") or []:
        meta = STRATEGY_CATALOG.get(str(strategy_id), {})
        minimum = max(minimum, int(meta.get("min_bars", 1)))
    return minimum + 1
