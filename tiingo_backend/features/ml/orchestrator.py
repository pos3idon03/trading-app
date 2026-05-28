from datetime import datetime
import base64
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import backtest_dal, instrument_dal, ml_model_dal
from features.backtesting.bar_loader import load_multi_timeframe_bars, validate_timeframe
from features.backtesting.engine import (
    run_backtest_with_signals,
    run_buy_and_hold_benchmark,
    serialize_simulation,
)
from features.backtesting.metrics import compute_metrics
from features.ml.artifacts import (
    build_feature_schema,
    delete_model_artifact,
    load_model_artifact,
    save_model_artifact,
    validate_feature_schema,
)
from features.ml.catalog import (
    feature_mode_uses_macro,
    list_ml_models,
    minimum_bars_required,
    resolve_fundamental_metrics,
    resolve_macro_series_ids,
    validate_inference_params,
    validate_ml_params,
)
from features.ml.data_preview import build_data_preview
from features.ml.evaluation import (
    build_confusion_matrix,
    build_roc_curves,
    compute_classification_metrics,
    extract_feature_importance,
)
from features.ml.explainability import compute_shap_importance
from features.ml.feature_builder import (
    _resolve_context_timeframes,
    _resolve_strategy_ids,
    build_ml_feature_matrix,
    collect_required_ml_timeframes,
)
from features.ml.context_features import build_context_feature_matrix
from features.ml.strategy_features import build_strategy_feature_matrix
from features.ml.hyperparameter_search import run_hyperparameter_search
from features.ml.inference_holdout import (
    build_holdout_train_metrics,
    collect_labeled_bar_indices,
    resolve_holdout_bars,
    resolve_inference_bar_load_range,
    resolve_inference_eval_scope,
    resolve_inference_window,
    split_holdout_indices,
    split_labeled_samples_by_indices,
)
from features.ml.label_search import DEFAULT_LABEL_SEARCH_MODEL_TYPES, run_label_grid_search
from features.ml.labels import build_labels
from features.ml.predictor import predict_with_frozen_model, run_walk_forward_prediction
from features.ml.simulation_window import (
    build_evaluation_metadata,
    build_simulation_metadata,
    resolve_evaluation_start_index,
    slice_simulation_window,
    walk_forward_simulation_start_index,
)
from features.ml.signals import count_signals, predictions_to_signals
from features.ml.threshold_search import run_threshold_search
from features.ml.trainer import train_model
from features.tiingo.entitlement import is_fundamentals_entitled


def _validate_fundamentals_entitlement(symbol: str, feature_mode: str) -> None:
    if feature_mode != "prices_macro_fundamentals":
        return
    settings = get_settings()
    if is_fundamentals_entitled(symbol, settings.tiingo_fundamentals_tier):
        return
    raise ValueError(
        f"Symbol {symbol.upper()} is not entitled for fundamentals under tier "
        f"{settings.tiingo_fundamentals_tier}. Use an entitled symbol or upgrade tier."
    )


def get_ml_model_catalog() -> list[dict]:
    return list_ml_models()


def _collect_labeled_samples(
    feature_rows: list[Optional[list[float]]],
    labels: list[Optional[int]],
) -> tuple[list[list[float]], list[int]]:
    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    for features, label in zip(feature_rows, labels):
        if features is None or label is None:
            continue
        x_rows.append(features)
        y_rows.append(label)
    return x_rows, y_rows


def _build_enriched_ml_summary(
    *,
    validated_params: dict,
    model_type: str,
    feature_names: list[str],
    macro_series_ids: list[str],
    macro_warnings: list[str],
    fundamental_metrics: list[str],
    fundamental_warnings: list[str],
    signals: list[str],
    run_mode: str,
    model_id: str | None,
    oos_window_count: int,
    mean_oos_accuracy: float | None,
    window_accuracies: list[float],
    y_true: list[int],
    y_pred: list[int],
    y_proba: list[list[float]],
    x_rows_for_shap: list[list[float]],
    model_classes: list[int],
    importance_model: Any | None,
    evaluation_metadata: dict | None = None,
) -> dict:
    label_mode = str(validated_params.get("label_mode") or "binary")
    metrics = compute_classification_metrics(y_true, y_pred)
    importance = (
        extract_feature_importance(importance_model, feature_names)
        if importance_model is not None
        else []
    )
    confusion_labels = sorted(set(y_true) | set(y_pred)) if y_true else [0, 1]
    roc_curves, auc_scores = build_roc_curves(y_true, y_proba, model_classes or confusion_labels)
    shap_rows: list[dict] = []
    shap_warnings: list[str] = []
    if importance_model is not None and x_rows_for_shap:
        try:
            shap_rows = compute_shap_importance(
                importance_model,
                x_rows_for_shap,
                feature_names,
                model_classes or confusion_labels,
            )
        except Exception as exc:
            shap_warnings.append(f"SHAP explainability skipped: {exc}")

    return {
        "feature_mode": validated_params["feature_mode"],
        "model_type": model_type,
        "label_mode": label_mode,
        "run_mode": run_mode,
        "model_id": model_id,
        "oos_window_count": oos_window_count,
        "mean_oos_accuracy": (
            round(mean_oos_accuracy, 4) if mean_oos_accuracy is not None else None
        ),
        "window_accuracies": [round(value, 4) for value in window_accuracies],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "f1_macro": metrics["f1_macro"],
        "confusion_matrix": build_confusion_matrix(
            y_true, y_pred, labels=confusion_labels,
        ),
        "confusion_labels": confusion_labels,
        "feature_importance": importance,
        "roc_curves": roc_curves,
        "auc_scores": auc_scores,
        "shap_importance": shap_rows,
        "signal_counts": count_signals(signals),
        "feature_names": feature_names,
        "macro_series_ids": macro_series_ids,
        "macro_warnings": [*macro_warnings, *shap_warnings],
        "fundamental_metrics": fundamental_metrics,
        "fundamental_period_type": validated_params.get("fundamental_period_type", "quarterly"),
        "fundamental_warnings": fundamental_warnings,
        "context_timeframes": list(validated_params.get("context_timeframes") or []),
        "strategy_feature_ids": list(validated_params.get("strategy_feature_ids") or []),
        **(evaluation_metadata or {}),
    }


async def _load_bars_and_features(
    session: AsyncSession,
    *,
    instrument: dict,
    validated_params: dict,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
) -> tuple[list[dict], list[str], list, list[str], list[str], list[str], list[str], list[str], list[str]]:
    from features.backtesting.bar_context import build_multi_timeframe_context

    required_tfs = collect_required_ml_timeframes(validated_params, timeframe)
    bars_by_tf = await load_multi_timeframe_bars(
        session,
        instrument["id"],
        required_tfs,
        start,
        end,
        decision_timeframe=timeframe,
    )
    bars = bars_by_tf[timeframe]
    min_bars = minimum_bars_required(validated_params)
    if len(bars) < min_bars:
        raise ValueError(
            f"Insufficient bars ({len(bars)}) for ML backtest. "
            f"Minimum required: {min_bars}"
        )

    bar_context = None
    if len(required_tfs) > 1:
        bar_context = build_multi_timeframe_context(
            decision_timeframe=timeframe,
            decision_bars=bars,
            bars_by_timeframe=bars_by_tf,
            standalone_signal_timeframe=timeframe,
        )

    (
        feature_names,
        feature_rows,
        macro_warnings,
        fundamental_warnings,
        macro_series_ids,
        fundamental_metrics,
        context_warnings,
        strategy_warnings,
    ) = await build_ml_feature_matrix(
        session,
        bars,
        validated_params,
        instrument_id=instrument["id"],
        decision_timeframe=timeframe,
        bar_context=bar_context,
    )
    all_macro_warnings = [*macro_warnings, *context_warnings, *strategy_warnings]
    return (
        bars,
        feature_names,
        feature_rows,
        all_macro_warnings,
        fundamental_warnings,
        macro_series_ids,
        fundamental_metrics,
        context_warnings,
        strategy_warnings,
    )


async def train_ml_model_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    name: str | None = None,
) -> dict:
    validate_timeframe(timeframe, "decision timeframe")
    validated_params = validate_ml_params(model_type, params, timeframe)

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    _validate_fundamentals_entitlement(instrument["symbol"], validated_params["feature_mode"])

    (
        _bars,
        feature_names,
        feature_rows,
        _macro_warnings,
        _fundamental_warnings,
        macro_series_ids,
        fundamental_metrics,
        _context_warnings,
        _strategy_warnings,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    labels = build_labels(
        _bars,
        int(validated_params["label_horizon"]),
        label_mode=str(validated_params.get("label_mode") or "binary"),
        label_threshold=float(validated_params.get("label_threshold") or 0.01),
        label_method=str(validated_params.get("label_method") or "endpoint"),
    )
    labeled_indices = collect_labeled_bar_indices(feature_rows, labels)
    holdout_bars = resolve_holdout_bars(validated_params)
    train_indices, holdout_indices = split_holdout_indices(labeled_indices, holdout_bars)
    x_rows, y_rows = split_labeled_samples_by_indices(feature_rows, labels, train_indices)
    if len(x_rows) < 2 or len(set(y_rows)) < 2:
        raise ValueError("Insufficient labeled train samples to train a model")

    trained = train_model(model_type, x_rows, y_rows, validated_params)
    predictions = [1 if prob >= 0.5 else 0 for prob in trained.model.predict(x_rows).tolist()]
    holdout_x, holdout_y = split_labeled_samples_by_indices(
        feature_rows,
        labels,
        holdout_indices,
    )
    holdout_predictions = [
        1 if prob >= 0.5 else 0 for prob in trained.model.predict(holdout_x).tolist()
    ]
    holdout_metrics = compute_classification_metrics(holdout_y, holdout_predictions)
    holdout_metadata = build_holdout_train_metrics(
        bars=_bars,
        train_indices=train_indices,
        holdout_indices=holdout_indices,
        holdout_bars=holdout_bars,
        decision_timeframe=timeframe,
        start=start,
        end=end,
    )
    train_metrics = {
        **compute_classification_metrics(y_rows, predictions),
        "train_accuracy": round(trained.train_accuracy, 4),
        "sample_count": len(y_rows),
        "holdout_accuracy": round(holdout_metrics["accuracy"], 4),
        "training_symbol": instrument["symbol"],
        "timeframe": timeframe,
        **holdout_metadata,
    }

    feature_schema = build_feature_schema(feature_names)
    model_name = name or (
        f"{instrument['symbol']} {model_type} {validated_params['feature_mode']}"
    )

    row = await ml_model_dal.create_model(
        session,
        name=model_name,
        model_type=model_type,
        feature_mode=validated_params["feature_mode"],
        feature_schema=feature_schema,
        hyperparams=validated_params,
        train_metrics=train_metrics,
        artifact_path=None,
    )
    artifact_path = save_model_artifact(trained.model, row["id"])
    row = await ml_model_dal.update_artifact_path(session, row["id"], artifact_path)
    await session.commit()
    return row


async def list_saved_ml_models(session: AsyncSession) -> list[dict]:
    return await ml_model_dal.list_models(session)


async def get_saved_ml_model(session: AsyncSession, model_id: UUID) -> dict | None:
    return await ml_model_dal.get_model(session, model_id)


async def delete_saved_ml_model(session: AsyncSession, model_id: UUID) -> None:
    row = await ml_model_dal.delete_model(session, model_id)
    if not row:
        raise LookupError(f"Saved model not found: {model_id}")
    delete_model_artifact(row.get("artifact_path"))
    await session.commit()


async def _run_walk_forward_backtest(
    *,
    model_type: str,
    validated_params: dict,
    feature_names: list[str],
    feature_rows: list,
    labels: list,
    bars: list[dict],
    macro_series_ids: list[str],
    macro_warnings: list[str],
    fundamental_metrics: list[str],
    fundamental_warnings: list[str],
) -> tuple[list[str], dict]:
    label_mode = str(validated_params.get("label_mode") or "binary")
    walk_forward = run_walk_forward_prediction(
        model_type=model_type,
        params=validated_params,
        feature_rows=feature_rows,
        labels=labels,
        train_bars=int(validated_params["train_bars"]),
        test_bars=int(validated_params["test_bars"]),
        step_bars=int(validated_params["step_bars"]),
    )
    min_class_probability = validated_params.get("min_class_probability")
    min_class_prob = float(min_class_probability) if min_class_probability is not None else None
    signals = predictions_to_signals(
        label_mode=label_mode,
        probabilities=walk_forward.probabilities,
        class_predictions=walk_forward.class_predictions,
        buy_threshold=float(validated_params["buy_threshold"]),
        sell_threshold=float(validated_params["sell_threshold"]),
        min_class_probability=min_class_prob,
        class_probabilities=walk_forward.class_probabilities,
    )
    ml_summary = _build_enriched_ml_summary(
        validated_params=validated_params,
        model_type=model_type,
        feature_names=feature_names,
        macro_series_ids=macro_series_ids,
        macro_warnings=macro_warnings,
        fundamental_metrics=fundamental_metrics,
        fundamental_warnings=fundamental_warnings,
        signals=signals,
        run_mode="walk_forward",
        model_id=None,
        oos_window_count=walk_forward.oos_window_count,
        mean_oos_accuracy=walk_forward.mean_oos_accuracy,
        window_accuracies=walk_forward.window_accuracies,
        y_true=walk_forward.oos_y_true,
        y_pred=walk_forward.oos_y_pred,
        y_proba=walk_forward.oos_y_proba,
        x_rows_for_shap=walk_forward.oos_x_rows,
        model_classes=walk_forward.model_classes,
        importance_model=walk_forward.last_trained_model,
    )
    return signals, ml_summary


async def _run_inference_backtest(
    *,
    session: AsyncSession,
    model_id: UUID,
    validated_params: dict,
    feature_names: list[str],
    feature_rows: list,
    labels: list,
    bars: list[dict],
    macro_series_ids: list[str],
    macro_warnings: list[str],
    fundamental_metrics: list[str],
    fundamental_warnings: list[str],
    eval_start_index: int = 0,
    evaluation_metadata: dict | None = None,
) -> tuple[list[str], dict, str]:
    saved = await ml_model_dal.get_model(session, model_id)
    if not saved:
        raise ValueError(f"Saved model not found: {model_id}")
    if not saved.get("artifact_path"):
        raise ValueError(f"Saved model {model_id} has no artifact on disk")

    validate_inference_params(saved, validated_params)
    validate_feature_schema(saved["feature_schema"], feature_names)

    label_mode = str(validated_params.get("label_mode") or "binary")
    model = load_model_artifact(saved["artifact_path"])
    probabilities, class_probabilities, class_predictions = predict_with_frozen_model(
        model,
        feature_rows,
        label_mode=label_mode,
    )
    min_class_probability = validated_params.get("min_class_probability")
    min_class_prob = float(min_class_probability) if min_class_probability is not None else None
    signals = predictions_to_signals(
        label_mode=label_mode,
        probabilities=probabilities,
        class_predictions=class_predictions,
        buy_threshold=float(validated_params["buy_threshold"]),
        sell_threshold=float(validated_params["sell_threshold"]),
        min_class_probability=min_class_prob,
        class_probabilities=class_probabilities,
    )

    aligned_y_true: list[int] = []
    aligned_y_pred: list[int] = []
    aligned_y_proba: list[list[float]] = []
    aligned_x_rows: list[list[float]] = []
    for index, (features, label, prob, class_pred, class_probs) in enumerate(
        zip(
            feature_rows,
            labels,
            probabilities,
            class_predictions,
            class_probabilities,
        )
    ):
        if index < eval_start_index:
            continue
        if features is None or label is None or class_pred is None or class_probs is None:
            continue
        aligned_y_true.append(label)
        aligned_y_pred.append(int(class_pred))
        aligned_y_proba.append(class_probs)
        aligned_x_rows.append(features)

    eval_signals = signals[eval_start_index:] if eval_start_index > 0 else signals
    ml_summary = _build_enriched_ml_summary(
        validated_params=validated_params,
        model_type=saved["model_type"],
        feature_names=feature_names,
        macro_series_ids=macro_series_ids,
        macro_warnings=macro_warnings,
        fundamental_metrics=fundamental_metrics,
        fundamental_warnings=fundamental_warnings,
        signals=eval_signals,
        run_mode="inference",
        model_id=str(model_id),
        oos_window_count=0,
        mean_oos_accuracy=None,
        window_accuracies=[],
        y_true=aligned_y_true,
        y_pred=aligned_y_pred,
        y_proba=aligned_y_proba,
        x_rows_for_shap=aligned_x_rows,
        model_classes=list(model.classes_),
        importance_model=model,
        evaluation_metadata=evaluation_metadata,
    )
    return signals, ml_summary, saved["model_type"]


async def run_ml_backtest_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    initial_cash: float,
    commission_bps: float,
) -> dict:
    validate_timeframe(timeframe, "decision timeframe")

    raw_params = dict(params or {})
    model_id_raw = raw_params.pop("model_id", None)
    model_id = UUID(str(model_id_raw)) if model_id_raw else None

    validated_params = validate_ml_params(model_type, raw_params, timeframe)

    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    _validate_fundamentals_entitlement(instrument["symbol"], validated_params["feature_mode"])

    saved_model: dict | None = None
    if model_id:
        saved_model = await ml_model_dal.get_model(session, model_id)
        if not saved_model:
            raise ValueError(f"Saved model not found: {model_id}")
        start, end = resolve_inference_bar_load_range(
            train_metrics=saved_model.get("train_metrics"),
            request_start=start,
            request_end=end,
        )

    run = await backtest_dal.create_run(
        session,
        instrument_id=instrument["id"],
        symbol=instrument["symbol"],
        strategy=model_type,
        params={**validated_params, **({"model_id": str(model_id)} if model_id else {})},
        timeframe=timeframe,
        start_date=start,
        end_date=end,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
    )
    await session.commit()

    try:
        (
            bars,
            feature_names,
            feature_rows,
            macro_warnings,
            fundamental_warnings,
            macro_series_ids,
            fundamental_metrics,
            _context_warnings,
            _strategy_warnings,
        ) = await _load_bars_and_features(
            session,
            instrument=instrument,
            validated_params=validated_params,
            timeframe=timeframe,
            start=start,
            end=end,
        )
        labels = build_labels(
            bars,
            int(validated_params["label_horizon"]),
            label_mode=str(validated_params.get("label_mode") or "binary"),
            label_threshold=float(validated_params.get("label_threshold") or 0.01),
            label_method=str(validated_params.get("label_method") or "endpoint"),
        )

        effective_model_type = model_type
        eval_start_index = 0
        if model_id:
            if saved_model is None:
                raise ValueError(f"Saved model not found: {model_id}")
            inference_eval_scope = resolve_inference_eval_scope(validated_params)
            eval_start_index, scope_metadata = resolve_inference_window(
                train_metrics=saved_model.get("train_metrics"),
                hyperparams=saved_model.get("hyperparams") or validated_params,
                inference_eval_scope=inference_eval_scope,
            )
            signals, ml_summary, effective_model_type = await _run_inference_backtest(
                session=session,
                model_id=model_id,
                validated_params=validated_params,
                feature_names=feature_names,
                feature_rows=feature_rows,
                labels=labels,
                bars=bars,
                macro_series_ids=macro_series_ids,
                macro_warnings=macro_warnings,
                fundamental_metrics=fundamental_metrics,
                fundamental_warnings=fundamental_warnings,
                eval_start_index=eval_start_index,
                evaluation_metadata=scope_metadata,
            )
        else:
            signals, ml_summary = await _run_walk_forward_backtest(
                model_type=model_type,
                validated_params=validated_params,
                feature_names=feature_names,
                feature_rows=feature_rows,
                labels=labels,
                bars=bars,
                macro_series_ids=macro_series_ids,
                macro_warnings=macro_warnings,
                fundamental_metrics=fundamental_metrics,
                fundamental_warnings=fundamental_warnings,
            )
            ml_summary = {**ml_summary, "evaluation_scope": "walk_forward_oos"}

        run_mode = "inference" if model_id else "walk_forward"
        bars_for_sim = bars
        signals_for_sim = signals
        sim_start = 0
        if run_mode == "walk_forward":
            sim_start = walk_forward_simulation_start_index(
                int(validated_params["train_bars"]),
            )
            bars_for_sim, signals_for_sim = slice_simulation_window(
                bars,
                signals,
                sim_start,
            )
            ml_summary = {
                **ml_summary,
                **build_simulation_metadata(
                    bars=bars,
                    start_index=sim_start,
                    decision_timeframe=timeframe,
                ),
                "signal_counts": count_signals(signals_for_sim),
            }
        elif eval_start_index > 0:
            sim_start = eval_start_index
            bars_for_sim, signals_for_sim = slice_simulation_window(
                bars,
                signals,
                sim_start,
            )
            ml_summary = {
                **ml_summary,
                **build_simulation_metadata(
                    bars=bars,
                    start_index=sim_start,
                    decision_timeframe=timeframe,
                ),
                "signal_counts": count_signals(signals_for_sim),
            }

        strategy_result = run_backtest_with_signals(
            bars_for_sim,
            signals_for_sim,
            initial_cash,
            commission_bps,
            decision_timeframe=timeframe,
        )
        eval_offset = resolve_evaluation_start_index(
            bars_for_sim,
            strategy_result.trades,
            decision_timeframe=timeframe,
        )
        if eval_offset > 0:
            eval_bars, eval_signals = slice_simulation_window(
                bars_for_sim,
                signals_for_sim,
                eval_offset,
            )
            strategy_result = run_backtest_with_signals(
                eval_bars,
                eval_signals,
                initial_cash,
                commission_bps,
                decision_timeframe=timeframe,
            )
            benchmark_result = run_buy_and_hold_benchmark(
                eval_bars,
                initial_cash,
                commission_bps,
                decision_timeframe=timeframe,
            )
        else:
            benchmark_result = run_buy_and_hold_benchmark(
                bars_for_sim,
                initial_cash,
                commission_bps,
                decision_timeframe=timeframe,
            )

        eval_reason = "first_trade" if strategy_result.trades else "simulation_start"
        ml_summary = {
            **ml_summary,
            **build_evaluation_metadata(
                bars=bars,
                start_index=sim_start + eval_offset,
                decision_timeframe=timeframe,
                reason=eval_reason,
            ),
        }
        metrics = compute_metrics(strategy_result, benchmark_result, initial_cash, timeframe)
        strategy_payload = serialize_simulation(strategy_result)
        benchmark_payload = serialize_simulation(benchmark_result)

        final_params = {**validated_params, "ml_summary": ml_summary}
        if model_id:
            final_params["model_id"] = str(model_id)

        await backtest_dal.finish_run(
            session,
            run["id"],
            status="completed",
            metrics=metrics,
            equity_curve=strategy_payload["equity_curve"],
            trades=strategy_payload["trades"],
            benchmark={"equity_curve": benchmark_payload["equity_curve"], "metrics": metrics},
        )
        await _update_run_params(session, run["id"], final_params)
        await session.commit()

        return {
            **run,
            "strategy": effective_model_type,
            "params": final_params,
            "status": "completed",
            "metrics": metrics,
            "equity_curve": strategy_payload["equity_curve"],
            "trades": strategy_payload["trades"],
            "benchmark": benchmark_payload,
            "ml_summary": ml_summary,
        }
    except Exception as exc:
        await backtest_dal.finish_run(
            session,
            run["id"],
            status="failed",
            error_message=str(exc),
        )
        await session.commit()
        raise


async def _update_run_params(session: AsyncSession, run_id, params: dict) -> None:
    from sqlalchemy import update

    from models.backtest import BacktestRun

    await session.execute(
        update(BacktestRun).where(BacktestRun.id == run_id).values(params=params),
    )


async def get_ml_backtest_results(session: AsyncSession, run_id) -> dict | None:
    row = await backtest_dal.get_run(session, run_id)
    if not row:
        return None
    ml_summary = (row.get("params") or {}).get("ml_summary")
    if ml_summary:
        row = {**row, "ml_summary": ml_summary}
    return row


async def _load_bars_by_timeframe(
    session: AsyncSession,
    instrument_id: int,
    validated_params: dict,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
) -> dict[str, list[dict]]:
    required_tfs = collect_required_ml_timeframes(validated_params, timeframe)
    return await load_multi_timeframe_bars(
        session,
        instrument_id,
        required_tfs,
        start,
        end,
        decision_timeframe=timeframe,
    )


async def _resolve_preview_warnings(
    session: AsyncSession,
    *,
    instrument_id: int,
    validated_params: dict,
    timeframe: str,
    bars_by_tf: dict[str, list[dict]],
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    if feature_mode_uses_macro(validated_params["feature_mode"]):
        macro_series_ids, macro_warnings = await resolve_macro_series_ids(session, validated_params)
    else:
        macro_series_ids, macro_warnings = [], []
    fundamental_metrics: list[str] = []
    fundamental_warnings: list[str] = []
    if validated_params["feature_mode"] == "prices_macro_fundamentals":
        fundamental_metrics, fundamental_warnings = await resolve_fundamental_metrics(
            session,
            instrument_id,
            validated_params,
        )

    context_warnings: list[str] = []
    strategy_warnings: list[str] = []
    bars = bars_by_tf[timeframe]
    context_tfs = _resolve_context_timeframes(validated_params, timeframe)
    if context_tfs and len(bars_by_tf) > 1:
        from features.backtesting.bar_context import build_multi_timeframe_context

        bar_context = build_multi_timeframe_context(
            decision_timeframe=timeframe,
            decision_bars=bars,
            bars_by_timeframe=bars_by_tf,
            standalone_signal_timeframe=timeframe,
        )
        _, _, context_warnings = build_context_feature_matrix(bar_context, context_tfs)

    strategy_ids = _resolve_strategy_ids(validated_params)
    if strategy_ids:
        params_map = validated_params.get("strategy_feature_params") or {}
        _, _, strategy_warnings = build_strategy_feature_matrix(
            bars,
            strategy_ids,
            params_map if isinstance(params_map, dict) else {},
        )

    return (
        macro_series_ids,
        macro_warnings,
        fundamental_metrics,
        fundamental_warnings,
        context_warnings,
        strategy_warnings,
    )


async def preview_ml_data_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    model_type: str = "ml_logistic",
) -> dict:
    validate_timeframe(timeframe, "decision timeframe")
    validated_params = validate_ml_params(model_type, params, timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")
    _validate_fundamentals_entitlement(instrument["symbol"], validated_params["feature_mode"])

    (
        bars,
        _feature_names,
        feature_rows,
        macro_warnings,
        fundamental_warnings,
        macro_series_ids,
        fundamental_metrics,
        context_warnings,
        strategy_warnings,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    bars_by_tf = await _load_bars_by_timeframe(
        session,
        instrument["id"],
        validated_params,
        timeframe,
        start,
        end,
    )
    preview = await build_data_preview(
        session,
        bars_by_timeframe=bars_by_tf,
        decision_timeframe=timeframe,
        validated_params=validated_params,
        macro_series_ids=macro_series_ids,
        fundamental_metrics=fundamental_metrics,
        context_warnings=[*context_warnings, *macro_warnings, *fundamental_warnings],
        strategy_warnings=strategy_warnings,
        bars=bars,
        feature_rows=feature_rows,
    )
    return preview


async def search_ml_labels_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    label_mode: str,
    horizons: list[int],
    thresholds: list[float],
    model_type: str | None = None,
    model_types: list[str] | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> list[dict]:
    validate_timeframe(timeframe, "decision timeframe")
    probe_model = model_type or (model_types[0] if model_types else "ml_logistic")
    validated_params = validate_ml_params(probe_model, params, timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    (
        bars,
        _feature_names,
        feature_rows,
        *_rest,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    resolved_models = model_types
    if resolved_models is None and model_type is not None:
        resolved_models = [model_type]
    if resolved_models is None:
        resolved_models = DEFAULT_LABEL_SEARCH_MODEL_TYPES

    combined: list[dict] = []
    total_models = len(resolved_models)
    for index, current_model in enumerate(resolved_models):
        combined.extend(run_label_grid_search(
            bars=bars,
            feature_rows=feature_rows,
            label_mode=label_mode,
            horizons=horizons,
            thresholds=thresholds,
            label_method=str(validated_params.get("label_method") or "endpoint"),
            train_bars=int(validated_params["train_bars"]),
            test_bars=int(validated_params["test_bars"]),
            step_bars=int(validated_params["step_bars"]),
            model_type=current_model,
        ))
        if on_progress is not None:
            on_progress(int(((index + 1) / max(total_models, 1)) * 100))

    combined.sort(
        key=lambda row: (
            row["f1_macro"] is not None,
            row["f1_macro"] or 0.0,
            row["accuracy"] or 0.0,
        ),
        reverse=True,
    )
    return combined


async def search_ml_thresholds_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    buy_thresholds: list[float],
    sell_thresholds: list[float],
) -> list[dict]:
    validate_timeframe(timeframe, "decision timeframe")
    validated_params = validate_ml_params(model_type, params, timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    (
        bars,
        feature_names,
        feature_rows,
        *_rest,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    labels = build_labels(
        bars,
        int(validated_params["label_horizon"]),
        label_mode=str(validated_params.get("label_mode") or "binary"),
        label_threshold=float(validated_params.get("label_threshold") or 0.01),
        label_method=str(validated_params.get("label_method") or "endpoint"),
    )
    walk_forward = run_walk_forward_prediction(
        model_type=model_type,
        params=validated_params,
        feature_rows=feature_rows,
        labels=labels,
        train_bars=int(validated_params["train_bars"]),
        test_bars=int(validated_params["test_bars"]),
        step_bars=int(validated_params["step_bars"]),
    )
    label_mode = str(validated_params.get("label_mode") or "binary")
    return run_threshold_search(
        label_mode=label_mode,
        probabilities=walk_forward.probabilities,
        class_predictions=walk_forward.class_predictions,
        class_probabilities=walk_forward.class_probabilities,
        y_true=walk_forward.oos_y_true,
        y_proba=walk_forward.oos_y_proba,
        buy_thresholds=buy_thresholds,
        sell_thresholds=sell_thresholds,
        min_class_probability=validated_params.get("min_class_probability"),
    )


async def search_ml_hyperparameters_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
) -> dict:
    validate_timeframe(timeframe, "decision timeframe")
    validated_params = validate_ml_params(model_type, params, timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    (
        bars,
        _feature_names,
        feature_rows,
        *_rest,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    labels = build_labels(
        bars,
        int(validated_params["label_horizon"]),
        label_mode=str(validated_params.get("label_mode") or "binary"),
        label_threshold=float(validated_params.get("label_threshold") or 0.01),
        label_method=str(validated_params.get("label_method") or "endpoint"),
    )
    x_rows, y_rows = _collect_labeled_samples(feature_rows, labels)
    if len(x_rows) < 2 or len(set(y_rows)) < 2:
        raise ValueError("Insufficient labeled samples for hyperparameter search")
    return run_hyperparameter_search(model_type, x_rows, y_rows, validated_params)


async def export_training_data_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    scope: str,
    sample_size: int = 500,
) -> dict:
    from features.ml.training_export import (
        build_training_rows,
        training_rows_to_excel_bytes,
    )

    validate_timeframe(timeframe, "decision timeframe")
    validated_params = validate_ml_params(model_type, params, timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    _validate_fundamentals_entitlement(instrument["symbol"], validated_params["feature_mode"])

    (
        bars,
        feature_names,
        feature_rows,
        *_rest,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    labels = build_labels(
        bars,
        int(validated_params["label_horizon"]),
        label_mode=str(validated_params.get("label_mode") or "binary"),
        label_threshold=float(validated_params.get("label_threshold") or 0.01),
        label_method=str(validated_params.get("label_method") or "endpoint"),
    )
    rows, warnings = build_training_rows(
        bars=bars,
        feature_names=feature_names,
        feature_rows=feature_rows,
        labels=labels,
        label_horizon=int(validated_params["label_horizon"]),
        label_method=str(validated_params.get("label_method") or "endpoint"),
        scope=scope,  # type: ignore[arg-type]
        sample_size=sample_size,
        train_bars=int(validated_params["train_bars"]),
        test_bars=int(validated_params["test_bars"]),
        step_bars=int(validated_params["step_bars"]),
    )
    if not rows:
        raise ValueError("No training rows available for export.")

    content = training_rows_to_excel_bytes(rows)
    filename = f"{instrument['symbol']}_{timeframe}_{scope}_training_data.xlsx"
    return {
        "filename": filename,
        "row_count": len(rows),
        "warnings": warnings,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }


async def export_workbook_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    model_type: str,
    params: dict | None,
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    training_scope: str,
    sample_size: int = 500,
    run_id=None,
    data_preview: dict | None = None,
    label_search_results: list | None = None,
    threshold_search_results: list | None = None,
    compare_results: list | None = None,
    config_snapshot: dict | None = None,
) -> dict:
    from features.ml.training_export import build_training_rows
    from features.ml.workbook_export import WorkbookInput, build_workbook_bytes

    validate_timeframe(timeframe, "decision timeframe")
    validated_params = validate_ml_params(model_type, params, timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise LookupError(f"Instrument not found: {symbol.upper()}")

    _validate_fundamentals_entitlement(instrument["symbol"], validated_params["feature_mode"])

    (
        bars,
        feature_names,
        feature_rows,
        *_rest,
    ) = await _load_bars_and_features(
        session,
        instrument=instrument,
        validated_params=validated_params,
        timeframe=timeframe,
        start=start,
        end=end,
    )
    labels = build_labels(
        bars,
        int(validated_params["label_horizon"]),
        label_mode=str(validated_params.get("label_mode") or "binary"),
        label_threshold=float(validated_params.get("label_threshold") or 0.01),
        label_method=str(validated_params.get("label_method") or "endpoint"),
    )
    rows, warnings = build_training_rows(
        bars=bars,
        feature_names=feature_names,
        feature_rows=feature_rows,
        labels=labels,
        label_horizon=int(validated_params["label_horizon"]),
        label_method=str(validated_params.get("label_method") or "endpoint"),
        scope=training_scope,  # type: ignore[arg-type]
        sample_size=sample_size,
        train_bars=int(validated_params["train_bars"]),
        test_bars=int(validated_params["test_bars"]),
        step_bars=int(validated_params["step_bars"]),
    )
    if not rows:
        raise ValueError("No training rows available for export.")

    run_results = None
    if run_id is not None:
        run_results = await get_ml_backtest_results(session, run_id)
        if not run_results:
            warnings.append(f"Backtest run not found: {run_id}")

    workbook = WorkbookInput(
        symbol=instrument["symbol"],
        model_type=model_type,
        timeframe=timeframe,
        params=validated_params,
        config_snapshot=config_snapshot,
        data_preview=data_preview,
        label_search_results=label_search_results,
        threshold_search_results=threshold_search_results,
        compare_results=compare_results,
        training_rows=rows,
        run_results=run_results,
    )
    content, sheet_metas = build_workbook_bytes(workbook)
    filename = f"{instrument['symbol']}_{timeframe}_ml_workbook.xlsx"
    return {
        "filename": filename,
        "row_count": len(rows),
        "warnings": warnings,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "sheets": [{"name": meta.name, "row_count": meta.row_count} for meta in sheet_metas],
    }

