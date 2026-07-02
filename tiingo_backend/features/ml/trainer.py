from dataclasses import dataclass
from typing import Any

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None  # type: ignore


@dataclass
class TrainResult:
    model: Any
    train_accuracy: float


TREE_MODEL_TYPES = frozenset({"ml_random_forest", "ml_gradient_boosting", "ml_xgboost"})
SCALED_MODEL_TYPES = frozenset({"ml_logistic", "ml_knn"})


class SafeKNeighborsClassifier(KNeighborsClassifier):
    """Caps n_neighbors to the training fold size so thin folds never crash."""

    def fit(self, X, y):
        sample_count = len(y)
        self.n_neighbors = min(self.n_neighbors, max(sample_count, 1))
        return super().fit(X, y)


def supports_feature_importance(model_type: str) -> bool:
    return model_type in TREE_MODEL_TYPES


def min_train_samples_for_model(model_type: str, params: dict) -> int:
    if model_type == "ml_knn":
        return max(1, int(params.get("knn_neighbors", 5)))
    if model_type == "ml_lstm":
        return max(2, int(params.get("lstm_seq_length", 32)))
    return 2


def _accuracy(y_true: list[int], y_pred: list[int]) -> float:
    if not y_true:
        return 0.0
    correct = sum(1 for truth, pred in zip(y_true, y_pred) if truth == pred)
    return correct / len(y_true)


def _scaled_pipeline(classifier: Any) -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", classifier),
    ])


def _resolve_classifier(model: Any) -> Any:
    if isinstance(model, Pipeline):
        classifier = model.named_steps.get("classifier")
        if classifier is not None:
            return classifier
    return model


def _model_classes(model: Any) -> list:
    return list(_resolve_classifier(model).classes_)


def _create_model(model_type: str, params: dict) -> Any:
    if model_type == "ml_logistic":
        return _scaled_pipeline(
            LogisticRegression(max_iter=5000, random_state=42),
        )
    if model_type == "ml_random_forest":
        estimators = int(params.get("random_forest_estimators", 100))
        return RandomForestClassifier(n_estimators=estimators, random_state=42, n_jobs=1)
    if model_type == "ml_gradient_boosting":
        max_iter = int(params.get("gradient_boosting_max_iter", 100))
        return HistGradientBoostingClassifier(max_iter=max_iter, random_state=42)
    if model_type == "ml_knn":
        neighbors = int(params.get("knn_neighbors", 5))
        return _scaled_pipeline(SafeKNeighborsClassifier(n_neighbors=neighbors))
    if model_type == "ml_xgboost":
        if XGBClassifier is None:
            raise ValueError("xgboost is not installed")
        return XGBClassifier(
            n_estimators=int(params.get("xgboost_estimators", 100)),
            max_depth=int(params.get("xgboost_max_depth", 6)),
            learning_rate=float(params.get("xgboost_learning_rate", 0.1)),
            random_state=42,
            eval_metric="mlogloss",
        )
    if model_type == "ml_lstm":
        from features.ml.models.lstm_classifier import LstmClassifier

        return LstmClassifier(
            seq_length=int(params.get("lstm_seq_length", 32)),
            hidden_size=int(params.get("lstm_hidden_size", 64)),
            num_layers=int(params.get("lstm_num_layers", 2)),
            epochs=int(params.get("lstm_epochs", 10)),
            dropout=float(params.get("lstm_dropout", 0.2)),
            learning_rate=float(params.get("lstm_learning_rate", 0.001)),
            batch_size=int(params.get("lstm_batch_size", 32)),
            early_stopping_patience=int(params.get("lstm_early_stopping_patience", 3)),
            validation_fraction=float(params.get("lstm_validation_fraction", 0.15)),
        )
    raise ValueError(f"Unsupported model type: {model_type}")


def train_model(
    model_type: str,
    x_train: list[list[float]],
    y_train: list[int],
    params: dict,
) -> TrainResult:
    if model_type == "ml_knn":
        requested = int(params.get("knn_neighbors", 5))
        params = {**params, "knn_neighbors": min(requested, len(x_train))}
    model = _create_model(model_type, params)
    model.fit(x_train, y_train)
    predictions = model.predict(x_train).tolist()
    return TrainResult(model=model, train_accuracy=_accuracy(y_train, predictions))


def predict_class_probabilities(model: Any, x_rows: list[list[float]]) -> list[list[float]]:
    probabilities = model.predict_proba(x_rows)
    return [[float(value) for value in row] for row in probabilities]


def predict_proba_up(model: Any, x_rows: list[list[float]]) -> list[float]:
    matrix = predict_class_probabilities(model, x_rows)
    classes = _model_classes(model)
    if 1 in classes:
        up_index = classes.index(1)
        return [row[up_index] for row in matrix]
    if 2 in classes:
        up_index = classes.index(2)
        return [row[up_index] for row in matrix]
    return [row[-1] for row in matrix]


def predict_labels_from_proba(
    model: Any,
    x_rows: list[list[float]],
    *,
    label_mode: str = "binary",
) -> list[int]:
    matrix = predict_class_probabilities(model, x_rows)
    classes = _model_classes(model)
    labels: list[int] = []
    for row in matrix:
        best_index = max(range(len(row)), key=lambda idx: row[idx])
        labels.append(int(classes[best_index]))
    if label_mode == "binary":
        return [1 if label == max(classes) else 0 for label in labels]
    return labels
