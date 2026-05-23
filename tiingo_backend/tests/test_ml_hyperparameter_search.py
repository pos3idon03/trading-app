import json

import pytest

from features.ml.hyperparameter_search import (
    model_supports_hyperparameter_search,
    run_hyperparameter_search,
)


@pytest.mark.parametrize(
    "model_type",
    ["ml_logistic", "ml_gradient_boosting", "ml_random_forest"],
)
def test_hyperparameter_search_result_is_json_serializable(model_type: str) -> None:
    x_train = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0], [6.0, 7.0]]
    y_train = [0, 1, 0, 1, 0, 1]

    result = run_hyperparameter_search(model_type, x_train, y_train, {})

    json.dumps(result)
    assert "model" not in result
    assert "best_params" in result
    assert "best_score" in result
    assert "tuned" in result


def test_logistic_regression_is_not_tuned() -> None:
    x_train = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0], [6.0, 7.0]]
    y_train = [0, 1, 0, 1, 0, 1]

    result = run_hyperparameter_search("ml_logistic", x_train, y_train, {})

    assert result["tuned"] is False
    assert result["best_params"] == {}
    assert result["best_score"] is None


def test_gradient_boosting_normalizes_best_params() -> None:
    x_train = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0], [6.0, 7.0]]
    y_train = [0, 1, 0, 1, 0, 1]

    result = run_hyperparameter_search("ml_gradient_boosting", x_train, y_train, {})

    assert result["tuned"] is True
    assert "max_iter" not in result["best_params"]
    assert "gradient_boosting_max_iter" in result["best_params"]


def test_model_supports_hyperparameter_search_flags() -> None:
    assert model_supports_hyperparameter_search("ml_logistic") is False
    assert model_supports_hyperparameter_search("ml_random_forest") is True
