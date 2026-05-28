import io

import pandas as pd
import pytest

from features.ml.workbook_export import (
    WorkbookInput,
    build_overview_rows,
    build_workbook_bytes,
    collect_workbook_specs,
    sanitize_sheet_name,
    sheet_config_rows,
)


def _minimal_workbook(**overrides) -> WorkbookInput:
    base = WorkbookInput(
        symbol="AAPL",
        model_type="ml_logistic",
        timeframe="1d",
        params={"label_horizon": 4, "train_bars": 252},
        config_snapshot={"initial_cash": 10_000, "run_mode": "walk_forward"},
        data_preview={
            "decision_timeframe": "1d",
            "warmup_bars_excluded": 20,
            "bar_counts": {"1d": 500},
            "label_preview": {
                "label_mode": "binary",
                "label_horizon": 4,
                "class_distribution": {"0": 120, "1": 110},
            },
            "walk_forward_readiness": {
                "viable_folds": 3,
                "train_bars": 252,
                "test_bars": 63,
            },
            "warnings": [],
            "macro_coverage": [],
        },
        label_search_results=None,
        threshold_search_results=None,
        compare_results=None,
        training_rows=[
            {"date": "2024-01-01", "ret_1": 0.1, "label": 1, "forward_return": 0.02},
            {"date": "2024-01-02", "ret_1": -0.2, "label": 0, "forward_return": -0.01},
        ],
        run_results=None,
    )
    return WorkbookInput(**{**base.__dict__, **overrides})


def test_sanitize_sheet_name_truncates_and_replaces_invalid_chars():
    assert sanitize_sheet_name("Equity:Curve/Test?") == "Equity_Curve_Test_"
    assert len(sanitize_sheet_name("x" * 40)) == 31


def test_build_overview_rows_lists_sheets():
    sheets = [
        type("Meta", (), {"name": "Config", "description": "Config snapshot", "row_count": 5})(),
        type("Meta", (), {"name": "Training_Data", "description": "Training rows", "row_count": 100})(),
    ]
    rows = build_overview_rows(sheets)
    assert rows[0]["Sheet"] == "Config"
    assert rows[1]["Rows"] == 100


def test_collect_workbook_specs_omits_optional_session_sheets():
    specs = collect_workbook_specs(_minimal_workbook())
    names = [spec.name for spec in specs]
    assert "Config" in names
    assert "Data_Preview" in names
    assert "Training_Data" in names
    assert "Label_Search" not in names
    assert "Threshold_Search" not in names
    assert "Macro_Coverage" not in names


def test_collect_workbook_specs_includes_label_and_threshold_when_present():
    workbook = _minimal_workbook(
        label_search_results=[
            {
                "label_key": "h4_t0.01",
                "label_horizon": 4,
                "class_distribution": {"0": 10, "1": 8},
            },
        ],
        threshold_search_results=[
            {
                "buy_threshold": 0.6,
                "sell_threshold": 0.4,
                "signal_counts": {"buy": 3, "sell": 2, "hold": 10},
            },
        ],
        data_preview={
            "decision_timeframe": "1d",
            "warmup_bars_excluded": 0,
            "bar_counts": {"1d": 100},
            "label_preview": {"class_distribution": {}},
            "macro_coverage": [
                {
                    "series_id": "CPI",
                    "total_observations": 100,
                    "with_release_date": 90,
                    "release_date_pct": 90.0,
                },
            ],
            "warnings": [],
        },
    )
    names = [spec.name for spec in collect_workbook_specs(workbook)]
    assert "Label_Search" in names
    assert "Threshold_Search" in names
    assert "Macro_Coverage" in names


def test_build_workbook_bytes_overview_is_first_sheet():
    content, sheets = build_workbook_bytes(_minimal_workbook())
    assert content.startswith(b"PK")
    assert sheets[0].name == "Overview"

    workbook = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
    assert workbook.sheet_names[0] == "Overview"
    overview = pd.read_excel(workbook, sheet_name="Overview")
    assert "Sheet" in overview.columns
    assert "Training_Data" in overview["Sheet"].tolist()


def test_build_workbook_bytes_includes_run_result_sheets():
    run_results = {
        "metrics": {"total_return_pct": 12.5, "sharpe_ratio": 1.1},
        "equity_curve": [
            {"date": "2024-01-01", "equity": 10_000, "cash": 0, "shares": 100, "drawdown_pct": 0},
        ],
        "benchmark": {
            "equity_curve": [
                {"date": "2024-01-01", "equity": 10_000, "cash": 0, "shares": 100, "drawdown_pct": 0},
            ],
        },
        "trades": [
            {
                "entry_date": "2024-01-01",
                "exit_date": "2024-01-05",
                "entry_price": 100,
                "exit_price": 105,
                "shares": 10,
                "pnl": 50,
                "pnl_pct": 5,
            },
        ],
        "ml_summary": {
            "feature_mode": "prices_only",
            "model_type": "ml_logistic",
            "oos_window_count": 2,
            "mean_oos_accuracy": 0.55,
            "signal_counts": {"buy": 1, "sell": 1, "hold": 8},
            "confusion_matrix": [[3, 1], [2, 4]],
            "confusion_labels": [0, 1],
            "window_accuracies": [0.5, 0.6],
            "feature_importance": [{"name": "ret_1", "value": 0.4}],
            "shap_importance": [{"class_label": "1", "feature": "ret_1", "mean_abs_shap": 0.2}],
            "roc_curves": [{"class_label": "1", "fpr": [0.0, 1.0], "tpr": [0.0, 1.0]}],
        },
    }
    content, sheets = build_workbook_bytes(_minimal_workbook(run_results=run_results))
    names = [sheet.name for sheet in sheets]
    assert "Equity_Curve" in names
    assert "Trades" in names
    assert "ML_Summary" in names
    assert "Confusion_Matrix" in names

    equity = pd.read_excel(io.BytesIO(content), sheet_name="Equity_Curve", engine="openpyxl")
    assert len(equity) == 2


def test_sheet_config_rows_includes_snapshot_and_params():
    rows = sheet_config_rows(_minimal_workbook())
    keys = {row["key"] for row in rows}
    assert "symbol" in keys
    assert "config.initial_cash" in keys
    assert "params.label_horizon" in keys


def test_build_workbook_bytes_raises_when_no_sections():
    workbook = WorkbookInput(
        symbol="AAPL",
        model_type="ml_logistic",
        timeframe="1d",
        params={},
        config_snapshot=None,
        data_preview=None,
        label_search_results=None,
        threshold_search_results=None,
        compare_results=None,
        training_rows=[],
        run_results=None,
    )
    with pytest.raises(ValueError, match="No workbook sections"):
        build_workbook_bytes(workbook)
