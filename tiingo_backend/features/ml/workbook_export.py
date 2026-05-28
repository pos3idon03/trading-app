import io
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from features.ml.training_export import order_training_dataframe

INVALID_SHEET_CHARS = re.compile(r"[:\\/?*\[\]]")
OVERVIEW_SHEET = "Overview"


@dataclass(frozen=True)
class SheetMeta:
    name: str
    description: str
    row_count: int


@dataclass(frozen=True)
class SheetSpec:
    name: str
    description: str
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class WorkbookInput:
    symbol: str
    model_type: str
    timeframe: str
    params: dict[str, Any]
    config_snapshot: dict[str, Any] | None
    data_preview: dict[str, Any] | None
    label_search_results: list[dict[str, Any]] | None
    threshold_search_results: list[dict[str, Any]] | None
    compare_results: list[dict[str, Any]] | None
    training_rows: list[dict[str, Any]]
    run_results: dict[str, Any] | None


def sanitize_sheet_name(name: str) -> str:
    cleaned = INVALID_SHEET_CHARS.sub("_", name.strip())
    return cleaned[:31] if cleaned else "Sheet"


def build_overview_rows(sheets: list[SheetMeta]) -> list[dict[str, Any]]:
    return [
        {"Sheet": sheet.name, "Description": sheet.description, "Rows": sheet.row_count}
        for sheet in sheets
    ]


def _append_flat_dict(prefix: str, data: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            _append_flat_dict(full_key, value, rows)
        elif isinstance(value, list):
            rows.append({"key": full_key, "value": ", ".join(str(item) for item in value)})
        else:
            rows.append({"key": full_key, "value": value})


def sheet_config_rows(workbook: WorkbookInput) -> list[dict[str, Any]]:
    rows = [
        {"key": "symbol", "value": workbook.symbol},
        {"key": "model_type", "value": workbook.model_type},
        {"key": "timeframe", "value": workbook.timeframe},
    ]
    if workbook.config_snapshot:
        _append_flat_dict("config", workbook.config_snapshot, rows)
    if workbook.params:
        _append_flat_dict("params", workbook.params, rows)
    return rows


def sheet_data_preview_rows(preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"key": "decision_timeframe", "value": preview.get("decision_timeframe")},
        {"key": "warmup_bars_excluded", "value": preview.get("warmup_bars_excluded")},
    ]
    for timeframe, count in (preview.get("bar_counts") or {}).items():
        rows.append({"key": f"bar_counts.{timeframe}", "value": count})
    label_preview = preview.get("label_preview") or {}
    for key, value in label_preview.items():
        rows.append({"key": f"label_preview.{key}", "value": value})
    for class_label, count in (label_preview.get("class_distribution") or {}).items():
        rows.append({"key": f"class_distribution.{class_label}", "value": count})
    readiness = preview.get("walk_forward_readiness") or {}
    for key, value in readiness.items():
        if key == "readiness_issues" and isinstance(value, list):
            rows.append({"key": "walk_forward.readiness_issues", "value": "; ".join(value)})
        else:
            rows.append({"key": f"walk_forward.{key}", "value": value})
    for warning in preview.get("warnings") or []:
        rows.append({"key": "warning", "value": warning})
    return rows


def sheet_macro_coverage_rows(preview: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in (preview.get("macro_coverage") or [])]


def sheet_label_search_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in results:
        row = {key: value for key, value in item.items() if key != "class_distribution"}
        for class_label, count in (item.get("class_distribution") or {}).items():
            row[f"class_{class_label}"] = count
        rows.append(row)
    return rows


def sheet_threshold_search_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in results:
        row = {key: value for key, value in item.items() if key != "signal_counts"}
        for signal, count in (item.get("signal_counts") or {}).items():
            row[f"signal_{signal}"] = count
        rows.append(row)
    return rows


def sheet_training_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return rows


def sheet_ml_summary_rows(ml_summary: dict[str, Any]) -> list[dict[str, Any]]:
    skip_keys = {
        "confusion_matrix",
        "confusion_labels",
        "window_accuracies",
        "feature_importance",
        "shap_importance",
        "roc_curves",
        "auc_scores",
        "feature_names",
        "macro_series_ids",
        "macro_warnings",
        "fundamental_metrics",
        "fundamental_warnings",
        "context_timeframes",
        "strategy_feature_ids",
        "signal_counts",
    }
    rows: list[dict[str, Any]] = []
    for key, value in ml_summary.items():
        if key in skip_keys:
            continue
        rows.append({"metric": key, "value": value})
    for signal, count in (ml_summary.get("signal_counts") or {}).items():
        rows.append({"metric": f"signal_{signal}", "value": count})
    for feature in ml_summary.get("feature_names") or []:
        rows.append({"metric": "feature_name", "value": feature})
    for key, value in (ml_summary.get("auc_scores") or {}).items():
        rows.append({"metric": f"auc_{key}", "value": value})
    return rows


def sheet_confusion_matrix_rows(ml_summary: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = ml_summary.get("confusion_matrix") or []
    labels = ml_summary.get("confusion_labels") or list(range(len(matrix)))
    rows: list[dict[str, Any]] = []
    for row_index, row_values in enumerate(matrix):
        for col_index, value in enumerate(row_values):
            rows.append(
                {
                    "actual": labels[row_index] if row_index < len(labels) else row_index,
                    "predicted": labels[col_index] if col_index < len(labels) else col_index,
                    "count": value,
                },
            )
    return rows


def sheet_window_accuracy_rows(ml_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"window": index + 1, "accuracy": accuracy}
        for index, accuracy in enumerate(ml_summary.get("window_accuracies") or [])
    ]


def sheet_feature_importance_rows(ml_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in (ml_summary.get("feature_importance") or [])]


def sheet_shap_importance_rows(ml_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in (ml_summary.get("shap_importance") or [])]


def sheet_roc_point_rows(ml_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for curve in ml_summary.get("roc_curves") or []:
        class_label = curve.get("class_label")
        for index, fpr in enumerate(curve.get("fpr") or []):
            tpr_values = curve.get("tpr") or []
            rows.append(
                {
                    "class_label": class_label,
                    "index": index,
                    "fpr": fpr,
                    "tpr": tpr_values[index] if index < len(tpr_values) else None,
                },
            )
    return rows


def sheet_portfolio_metrics_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"metric": key, "value": value} for key, value in metrics.items()]


def sheet_equity_curve_rows(run_results: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for point in run_results.get("equity_curve") or []:
        rows.append({"series": "strategy", **point})
    for point in run_results.get("benchmark_equity_curve") or []:
        rows.append({"series": "benchmark", **point})
    benchmark = run_results.get("benchmark") or {}
    for point in benchmark.get("equity_curve") or []:
        rows.append({"series": "benchmark", **point})
    return rows


def sheet_trade_rows(run_results: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(trade) for trade in (run_results.get("trades") or [])]


def sheet_compare_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in results:
        feature_mode = item.get("feature_mode") or item.get("featureMode")
        label = item.get("label")
        error = item.get("error")
        run = item.get("run") or {}
        metrics = run.get("metrics") or {}
        ml_summary = run.get("ml_summary") or {}
        rows.append(
            {
                "feature_mode": feature_mode,
                "label": label,
                "error": error,
                "total_return_pct": metrics.get("total_return_pct"),
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "max_drawdown_pct": metrics.get("max_drawdown_pct"),
                "mean_oos_accuracy": ml_summary.get("mean_oos_accuracy"),
                "f1_macro": ml_summary.get("f1_macro"),
            },
        )
    return rows


def _spec(name: str, description: str, rows: list[dict[str, Any]]) -> SheetSpec | None:
    if not rows:
        return None
    return SheetSpec(name=sanitize_sheet_name(name), description=description, rows=rows)


def collect_workbook_specs(workbook: WorkbookInput) -> list[SheetSpec]:
    specs: list[SheetSpec] = []

    config_spec = _spec("Config", "Symbol, model, and wizard configuration snapshot", sheet_config_rows(workbook))
    if config_spec:
        specs.append(config_spec)

    if workbook.data_preview:
        preview_spec = _spec(
            "Data_Preview",
            "Data prep summary, label preview, and walk-forward readiness",
            sheet_data_preview_rows(workbook.data_preview),
        )
        if preview_spec:
            specs.append(preview_spec)
        macro_spec = _spec(
            "Macro_Coverage",
            "Macro ALFRED release-date coverage by series",
            sheet_macro_coverage_rows(workbook.data_preview),
        )
        if macro_spec:
            specs.append(macro_spec)

    if workbook.label_search_results:
        label_spec = _spec(
            "Label_Search",
            "Label grid search results across horizons and models",
            sheet_label_search_rows(workbook.label_search_results),
        )
        if label_spec:
            specs.append(label_spec)

    if workbook.threshold_search_results:
        threshold_spec = _spec(
            "Threshold_Search",
            "Buy/sell threshold grid search results",
            sheet_threshold_search_rows(workbook.threshold_search_results),
        )
        if threshold_spec:
            specs.append(threshold_spec)

    training_spec = _spec(
        "Training_Data",
        "Labeled feature matrix used for model training and export",
        sheet_training_rows(workbook.training_rows),
    )
    if training_spec:
        specs.append(training_spec)

    if workbook.run_results:
        ml_summary = workbook.run_results.get("ml_summary") or {}
        run_specs = [
            _spec("ML_Summary", "Out-of-sample ML metrics and run metadata", sheet_ml_summary_rows(ml_summary)),
            _spec("Confusion_Matrix", "Confusion matrix counts by actual vs predicted class", sheet_confusion_matrix_rows(ml_summary)),
            _spec("Window_Accuracies", "Per walk-forward window out-of-sample accuracy", sheet_window_accuracy_rows(ml_summary)),
            _spec("Feature_Importance", "Model feature importance values", sheet_feature_importance_rows(ml_summary)),
            _spec("SHAP_Importance", "Mean absolute SHAP values by class and feature", sheet_shap_importance_rows(ml_summary)),
            _spec("ROC_Points", "ROC curve points (one-vs-rest) by class", sheet_roc_point_rows(ml_summary)),
        ]
        metrics = workbook.run_results.get("metrics")
        if metrics:
            run_specs.append(
                _spec("Portfolio_Metrics", "Portfolio backtest performance metrics", sheet_portfolio_metrics_rows(metrics)),
            )
        run_specs.extend(
            [
                _spec("Equity_Curve", "Strategy and benchmark equity by date", sheet_equity_curve_rows(workbook.run_results)),
                _spec("Trades", "Simulated trade list", sheet_trade_rows(workbook.run_results)),
            ],
        )
        specs.extend(spec for spec in run_specs if spec)

    if workbook.compare_results:
        compare_spec = _spec(
            "Feature_Mode_Compare",
            "Feature mode comparison summary",
            sheet_compare_rows(workbook.compare_results),
        )
        if compare_spec:
            specs.append(compare_spec)

    return specs


def _dataframe_for_sheet(spec: SheetSpec) -> pd.DataFrame:
    frame = pd.DataFrame(spec.rows)
    if spec.name == sanitize_sheet_name("Training_Data"):
        return order_training_dataframe(frame)
    return frame


def _write_specs(writer: pd.ExcelWriter, specs: list[SheetSpec]) -> list[SheetMeta]:
    metas: list[SheetMeta] = []
    for spec in specs:
        frame = _dataframe_for_sheet(spec)
        frame.to_excel(writer, index=False, sheet_name=spec.name)
        metas.append(SheetMeta(name=spec.name, description=spec.description, row_count=len(frame)))
    return metas


def build_workbook_bytes(workbook: WorkbookInput) -> tuple[bytes, list[SheetMeta]]:
    specs = collect_workbook_specs(workbook)
    if not specs:
        raise ValueError("No workbook sections available for export.")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        data_metas = _write_specs(writer, specs)
        overview_rows = build_overview_rows(data_metas)
        overview_frame = pd.DataFrame(overview_rows)
        overview_frame.to_excel(writer, sheet_name=OVERVIEW_SHEET, index=False)
        overview_meta = SheetMeta(
            name=OVERVIEW_SHEET,
            description="Index of included sheets and row counts",
            row_count=len(overview_frame),
        )
        writer.book.move_sheet(OVERVIEW_SHEET, offset=-len(writer.book.sheetnames) + 1)

    all_metas = [overview_meta, *data_metas]
    buffer.seek(0)
    return buffer.read(), all_metas
