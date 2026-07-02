"""Walk-forward training thresholds for sparse meta-label event samples."""


def is_sparse_meta_label_training(
    params: dict,
    sample_mask: list[bool] | None,
) -> bool:
    if sample_mask is None:
        return False
    return str(params.get("label_mode") or "") == "meta_label"


def effective_lstm_seq_length(requested: int, row_count: int) -> int:
    if row_count <= 0:
        return max(2, requested)
    return max(2, min(requested, row_count))


def min_train_samples_for_fold(
    model_type: str,
    params: dict,
    *,
    sparse_events: bool,
) -> int:
    from features.ml.trainer import min_train_samples_for_model

    base = min_train_samples_for_model(model_type, params)
    if not sparse_events or model_type != "ml_lstm":
        return base

    seq = int(params.get("lstm_seq_length", 32))
    floor = int(params.get("meta_label_min_train_events", 4))
    return max(2, min(base, max(floor, seq // 4)))
