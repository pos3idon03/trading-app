from datetime import datetime, timedelta, timezone

from features.ml.catalog import validate_ml_params
from features.ml.labels import build_forward_return_labels
from features.ml.predictor import run_walk_forward_prediction
from features.ml.price_features import build_price_feature_matrix


def _bars(count: int, *, step: timedelta, start: datetime | None = None) -> list[dict]:
    rows = []
    base = start or datetime(2020, 1, 1, tzinfo=timezone.utc)
    for i in range(count):
        wave = 1 if (i // 10) % 2 == 0 else -1
        price = 100 + (i * 0.3 * wave)
        rows.append(
            {
                "time": base + (step * i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def _run_pipeline(bars: list[dict], timeframe: str) -> None:
    params = validate_ml_params("ml_logistic", {}, timeframe=timeframe)
    _, feature_rows = build_price_feature_matrix(bars)
    labels = build_forward_return_labels(bars, int(params["label_horizon"]))
    train_bars = min(int(params["train_bars"]), 120)
    test_bars = min(int(params["test_bars"]), 40)
    step_bars = min(int(params["step_bars"]), 40)
    result = run_walk_forward_prediction(
        model_type="ml_logistic",
        params=params,
        feature_rows=feature_rows,
        labels=labels,
        train_bars=train_bars,
        test_bars=test_bars,
        step_bars=step_bars,
    )
    predicted = [i for i, prob in enumerate(result.probabilities) if prob is not None]
    assert predicted
    assert min(predicted) >= train_bars


def test_walk_forward_succeeds_on_hourly_bars():
    bars = _bars(500, step=timedelta(hours=1))
    _run_pipeline(bars, "1h")


def test_walk_forward_succeeds_on_weekly_bars():
    bars = _bars(200, step=timedelta(weeks=1))
    _run_pipeline(bars, "1w")
