from typing import Any

from sklearn.model_selection import GridSearchCV

_SKLEARN_TO_APP_PARAMS: dict[str, dict[str, str]] = {
    "ml_random_forest": {"n_estimators": "random_forest_estimators"},
    "ml_gradient_boosting": {"max_iter": "gradient_boosting_max_iter"},
    "ml_knn": {
        "n_neighbors": "knn_neighbors",
        "classifier__n_neighbors": "knn_neighbors",
    },
    "ml_xgboost": {
        "max_depth": "xgboost_max_depth",
        "learning_rate": "xgboost_learning_rate",
    },
}


def model_supports_hyperparameter_search(
    model_type: str,
    params: dict | None = None,
) -> bool:
    return bool(_param_grid(model_type, params or {}))


def run_hyperparameter_search(
    model_type: str,
    x_train: list[list[float]],
    y_train: list[int],
    params: dict,
) -> dict[str, Any]:
    from features.ml.trainer import _create_model

    grid = _param_grid(model_type, params, sample_count=len(x_train))
    if not grid:
        model = _create_model(model_type, params)
        model.fit(x_train, y_train)
        return {"best_params": {}, "best_score": None, "tuned": False}

    estimator = _create_model(model_type, params)
    search = GridSearchCV(
        estimator,
        grid,
        scoring="f1_macro",
        cv=min(3, len(set(y_train))),
        n_jobs=1,
    )
    search.fit(x_train, y_train)
    return {
        "best_params": _normalize_best_params(model_type, dict(search.best_params_)),
        "best_score": round(float(search.best_score_), 4),
        "tuned": True,
    }


def _normalize_best_params(model_type: str, sklearn_params: dict[str, Any]) -> dict[str, Any]:
    mapping = _SKLEARN_TO_APP_PARAMS.get(model_type, {})
    normalized: dict[str, Any] = {}
    for sklearn_key, value in sklearn_params.items():
        app_key = mapping.get(sklearn_key)
        if app_key is None:
            continue
        normalized[app_key] = value
    return normalized


def _param_grid(
    model_type: str,
    params: dict,
    *,
    sample_count: int | None = None,
) -> dict[str, list[Any]]:
    if model_type == "ml_random_forest":
        return {
            "n_estimators": [
                int(params.get("random_forest_estimators", 100)),
                max(50, int(params.get("random_forest_estimators", 100)) // 2),
            ],
            "max_depth": [None, 8, 16],
        }
    if model_type == "ml_gradient_boosting":
        return {
            "max_iter": [
                int(params.get("gradient_boosting_max_iter", 100)),
                max(50, int(params.get("gradient_boosting_max_iter", 100)) // 2),
            ],
            "max_depth": [None, 8],
        }
    if model_type == "ml_knn":
        candidates = [3, 5, int(params.get("knn_neighbors", 7))]
        max_neighbors = sample_count if sample_count is not None else max(candidates)
        neighbors = sorted({value for value in candidates if value <= max_neighbors})
        if not neighbors:
            neighbors = [max(1, max_neighbors)]
        return {"classifier__n_neighbors": neighbors}
    if model_type == "ml_xgboost":
        return {
            "max_depth": [4, int(params.get("xgboost_max_depth", 6))],
            "learning_rate": [0.05, float(params.get("xgboost_learning_rate", 0.1))],
        }
    return {}
