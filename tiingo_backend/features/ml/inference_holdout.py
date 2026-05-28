from datetime import datetime

from features.ml.simulation_window import format_simulation_start_date

SUPPORTED_INFERENCE_EVAL_SCOPES = frozenset({"holdout", "in_sample"})


def collect_labeled_bar_indices(
    feature_rows: list,
    labels: list,
) -> list[int]:
    indices: list[int] = []
    for index, (features, label) in enumerate(zip(feature_rows, labels)):
        if features is None or label is None:
            continue
        indices.append(index)
    return indices


def split_holdout_indices(
    labeled_indices: list[int],
    holdout_bars: int,
) -> tuple[list[int], list[int]]:
    if holdout_bars < 1:
        raise ValueError("holdout_bars must be at least 1")
    if len(labeled_indices) <= holdout_bars:
        raise ValueError(
            f"Insufficient labeled bars ({len(labeled_indices)}) for holdout "
            f"({holdout_bars} bars). Increase the date range or reduce test_bars."
        )
    split_at = len(labeled_indices) - holdout_bars
    return labeled_indices[:split_at], labeled_indices[split_at:]


def resolve_holdout_bars(hyperparams: dict) -> int:
    return int(hyperparams.get("test_bars") or 63)


def split_labeled_samples_by_indices(
    feature_rows: list,
    labels: list,
    indices: list[int],
) -> tuple[list[list[float]], list[int]]:
    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    for index in indices:
        features = feature_rows[index]
        label = labels[index]
        if features is None or label is None:
            continue
        x_rows.append(features)
        y_rows.append(int(label))
    return x_rows, y_rows


def build_holdout_train_metrics(
    *,
    bars: list[dict],
    train_indices: list[int],
    holdout_indices: list[int],
    holdout_bars: int,
    decision_timeframe: str,
    start: datetime | None,
    end: datetime | None,
) -> dict:
    train_end_bar = bars[train_indices[-1]]
    holdout_start_bar = bars[holdout_indices[0]]
    holdout_end_bar = bars[holdout_indices[-1]]
    return {
        "holdout_bars": holdout_bars,
        "holdout_start_bar_index": holdout_indices[0],
        "holdout_start": format_simulation_start_date(holdout_start_bar, decision_timeframe),
        "holdout_end": format_simulation_start_date(holdout_end_bar, decision_timeframe),
        "train_end": format_simulation_start_date(train_end_bar, decision_timeframe),
        "train_sample_count": len(train_indices),
        "holdout_sample_count": len(holdout_indices),
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
    }


def resolve_inference_eval_scope(params: dict) -> str:
    raw = str(params.get("inference_eval_scope") or "holdout")
    if raw not in SUPPORTED_INFERENCE_EVAL_SCOPES:
        supported = ", ".join(sorted(SUPPORTED_INFERENCE_EVAL_SCOPES))
        raise ValueError(f"inference_eval_scope must be one of: {supported}")
    return raw


def resolve_inference_bar_load_range(
    *,
    train_metrics: dict | None,
    request_start: datetime | None,
    request_end: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    if not train_metrics:
        return request_start, request_end
    tm_start = train_metrics.get("start")
    tm_end = train_metrics.get("end")
    start = request_start
    end = request_end
    if isinstance(tm_start, str):
        start = datetime.fromisoformat(tm_start.replace("Z", "+00:00"))
    if isinstance(tm_end, str):
        end = datetime.fromisoformat(tm_end.replace("Z", "+00:00"))
    return start, end


def resolve_inference_window(
    *,
    train_metrics: dict | None,
    hyperparams: dict,
    inference_eval_scope: str,
) -> tuple[int, dict]:
    if inference_eval_scope == "in_sample":
        return 0, {
            "evaluation_scope": "in_sample",
            "holdout_bars": resolve_holdout_bars(hyperparams),
        }

    if not train_metrics or train_metrics.get("holdout_start") is None:
        raise ValueError("Retrain this model to enable holdout evaluation.")

    start_index = int(train_metrics["holdout_start_bar_index"])
    holdout_bars = int(train_metrics.get("holdout_bars") or resolve_holdout_bars(hyperparams))
    return start_index, {
        "evaluation_scope": "holdout",
        "holdout_bars": holdout_bars,
        "holdout_start_date": train_metrics.get("holdout_start"),
        "holdout_end_date": train_metrics.get("holdout_end"),
        "train_end_date": train_metrics.get("train_end"),
    }
