from features.ml.evaluation import compute_classification_metrics
from features.ml.signals import count_signals, predictions_to_signals


def run_threshold_search(
    *,
    label_mode: str,
    probabilities: list[float | None],
    class_predictions: list[int | None],
    class_probabilities: list[list[float] | None],
    y_true: list[int],
    y_proba: list[list[float]],
    buy_thresholds: list[float],
    sell_thresholds: list[float],
    min_class_probability: float | None = None,
) -> list[dict]:
    results: list[dict] = []

    if label_mode == "ternary":
        gates = [min_class_probability] if min_class_probability is not None else [None, 0.55, 0.6]
        for gate in gates:
            signals = predictions_to_signals(
                label_mode=label_mode,
                probabilities=probabilities,
                class_predictions=class_predictions,
                buy_threshold=0.55,
                sell_threshold=0.45,
                min_class_probability=gate,
                class_probabilities=class_probabilities,
            )
            aligned_true: list[int] = []
            aligned_pred: list[int] = []
            for truth, pred in zip(y_true, class_predictions):
                if pred is None:
                    continue
                aligned_true.append(truth)
                aligned_pred.append(pred)
            metrics = compute_classification_metrics(aligned_true, aligned_pred)
            results.append({
                "buy_threshold": None,
                "sell_threshold": None,
                "min_class_probability": gate,
                "signal_counts": count_signals(signals),
                **metrics,
            })
        return results

    for buy_threshold in buy_thresholds:
        for sell_threshold in sell_thresholds:
            if buy_threshold <= sell_threshold:
                continue
            signals = predictions_to_signals(
                label_mode=label_mode,
                probabilities=probabilities,
                buy_threshold=buy_threshold,
                sell_threshold=sell_threshold,
            )
            aligned_true: list[int] = []
            aligned_pred: list[int] = []
            for index, prob in enumerate(probabilities):
                if prob is None:
                    continue
                if index >= len(y_true):
                    break
                aligned_true.append(y_true[index] if index < len(y_true) else 0)
                aligned_pred.append(1 if prob >= 0.5 else 0)
            if y_true and y_proba:
                aligned_true = y_true
                aligned_pred = [1 if prob >= 0.5 else 0 for prob in [row[1] if len(row) > 1 else row[0] for row in y_proba]]
            metrics = compute_classification_metrics(aligned_true, aligned_pred)
            results.append({
                "buy_threshold": buy_threshold,
                "sell_threshold": sell_threshold,
                "min_class_probability": None,
                "signal_counts": count_signals(signals),
                **metrics,
            })

    results.sort(key=lambda row: (row.get("f1_macro") or 0.0, row.get("f1") or 0.0), reverse=True)
    return results
