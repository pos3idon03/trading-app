from datetime import date, datetime, timedelta, timezone

from features.ml.assembler import assemble_feature_matrix
from features.ml.fundamental_features import build_fundamental_feature_matrix
from features.ml.labels import build_forward_return_labels
from features.ml.macro_features import build_macro_feature_matrix
from features.ml.predictor import run_walk_forward_prediction
from features.ml.price_features import build_price_feature_matrix


def _daily_bars(count: int, start: date | None = None) -> list[dict]:
    base = start or date(2020, 1, 1)
    rows = []
    for i in range(count):
        wave = 1 if (i // 10) % 2 == 0 else -1
        price = 100 + (i * 0.2 * wave)
        rows.append(
            {
                "time": datetime.combine(base + timedelta(days=i), datetime.min.time(), tzinfo=timezone.utc),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "div_cash": 0,
                "split_factor": 1,
            }
        )
    return rows


def _daily_obs(count: int, start: date) -> list[dict]:
    return [
        {"obs_date": start + timedelta(days=i), "value": 4.0 + (i * 0.01)}
        for i in range(count)
    ]


def _fundamental_rows(metric: str, start: date, count: int) -> list[dict]:
    rows = []
    for i in range(count):
        report_date = start + timedelta(days=i * 90)
        year = report_date.year
        quarter = (report_date.month - 1) // 3 + 1
        rows.append(
            {
                "time": datetime.combine(report_date, datetime.min.time(), tzinfo=timezone.utc),
                "metric_name": metric,
                "value": 100.0 + i * 5,
                "period": f"{year}-Q{quarter}",
                "statement_type": "incomeStatement",
            }
        )
    return rows


def test_walk_forward_with_prices_macro_fundamentals_features():
    bars = _daily_bars(500, start=date(2020, 1, 1))
    obs = _daily_obs(500, date(2018, 6, 1))
    fund_rows = _fundamental_rows("revenue", date(2018, 3, 1), 12)
    price_names, price_rows = build_price_feature_matrix(bars)
    macro_names, macro_rows, _ = build_macro_feature_matrix(bars, {"DFF": obs}, ["DFF"])
    fund_names, fund_rows, _ = build_fundamental_feature_matrix(
        bars,
        {"revenue": fund_rows},
        ["revenue"],
        "quarterly",
    )
    feature_names, feature_rows = assemble_feature_matrix(
        "prices_macro_fundamentals",
        price_names,
        price_rows,
        macro_names,
        macro_rows,
        fund_names,
        fund_rows,
    )
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
    assert len(feature_names) > len(price_names)
    assert "revenue_level" in feature_names
    assert "DFF_level" in feature_names
    assert result.oos_window_count >= 1
