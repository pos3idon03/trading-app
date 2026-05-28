from datetime import datetime, timedelta, timezone

from features.ml.labels import build_forward_return_labels
from features.ml.predictor import run_walk_forward_prediction
from features.ml.price_features import build_price_feature_matrix


def _bars(count: int) -> list[dict]:
    rows = []
    for i in range(count):
        wave = 1 if (i // 10) % 2 == 0 else -1
        price = 100 + (i * 0.3 * wave)
        rows.append(
            {
                "time": datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def test_walk_forward_predictions_only_on_oos_indices():
    bars = _bars(500)
    _, feature_rows = build_price_feature_matrix(bars)
    labels = build_forward_return_labels(bars, label_horizon=5)

    result = run_walk_forward_prediction(
        model_type="ml_logistic",
        params={},
        feature_rows=feature_rows,
        labels=labels,
        train_bars=120,
        test_bars=40,
        step_bars=40,
    )

    assert result.oos_window_count >= 1
    predicted_indices = [i for i, prob in enumerate(result.probabilities) if prob is not None]
    assert predicted_indices
    assert min(predicted_indices) >= 120
    assert len(result.window_accuracies) == result.oos_window_count
    assert len(result.oos_y_true) > 0
    assert len(result.oos_y_pred) == len(result.oos_y_true)


def test_walk_forward_knn_skips_folds_below_neighbor_count():
    bar_count = 250
    train_bars, test_bars, step_bars = 150, 50, 50
    feature_rows: list[list[float] | None] = [None] * bar_count
    for index in range(147, bar_count):
        feature_rows[index] = [float(index), float(index) * 0.1]
    labels = [0 if index % 2 == 0 else 1 for index in range(bar_count)]

    result = run_walk_forward_prediction(
        model_type="ml_knn",
        params={"knn_neighbors": 5},
        feature_rows=feature_rows,
        labels=labels,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
    )

    assert result.oos_window_count >= 1
