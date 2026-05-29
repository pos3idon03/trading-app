from unittest.mock import AsyncMock, patch

import pytest

from features.ml import orchestrator
from features.ml.data_preview import build_data_preview
from features.ml.price_features import build_price_feature_matrix


def _sample_bars(count: int = 60) -> list[dict]:
    closes = [100.0]
    for idx in range(1, count):
        closes.append(closes[-1] * (1 + 0.002 * (1 if idx % 3 else -1)))
    return [
        {"time": f"2024-01-{idx:02d}", "close": c, "high": c * 1.01, "low": c * 0.99}
        for idx, c in enumerate(closes, start=1)
    ]


@pytest.mark.asyncio
async def test_build_data_preview_skips_macro_coverage_for_prices_only():
    bars_by_tf = {"1d": _sample_bars()}
    validated_params = {"feature_mode": "prices_only", "label_horizon": 5}

    with patch(
        "features.ml.data_preview.macro_dal.get_release_date_coverage_batch",
        new=AsyncMock(),
    ) as mock_coverage:
        result = await build_data_preview(
            AsyncMock(),
            bars_by_timeframe=bars_by_tf,
            decision_timeframe="1d",
            validated_params=validated_params,
            macro_series_ids=["DFF", "CPIAUCSL"],
            fundamental_metrics=[],
            context_warnings=[],
            strategy_warnings=[],
        )

    assert result["macro_coverage"] == []
    assert not any("Macro series" in warning for warning in result["warnings"])
    mock_coverage.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_data_preview_includes_macro_coverage_for_prices_macro():
    bars_by_tf = {"1d": _sample_bars()}
    validated_params = {"feature_mode": "prices_macro", "label_horizon": 5}
    coverage_payload = {
        "DFF": {"total": 10, "with_release_date": 10, "pct": 100.0},
        "CPIAUCSL": {"total": 8, "with_release_date": 4, "pct": 50.0},
    }

    with patch(
        "features.ml.data_preview.macro_dal.get_release_date_coverage_batch",
        new=AsyncMock(return_value=coverage_payload),
    ) as mock_coverage:
        result = await build_data_preview(
            AsyncMock(),
            bars_by_timeframe=bars_by_tf,
            decision_timeframe="1d",
            validated_params=validated_params,
            macro_series_ids=["DFF", "CPIAUCSL"],
            fundamental_metrics=[],
            context_warnings=[],
            strategy_warnings=[],
        )

    mock_coverage.assert_awaited_once()
    assert len(result["macro_coverage"]) == 2
    assert result["macro_coverage"][1]["series_id"] == "CPIAUCSL"
    assert any("Macro series CPIAUCSL" in warning for warning in result["warnings"])


@pytest.mark.asyncio
async def test_build_data_preview_includes_walk_forward_readiness():
    bars = _sample_bars(300)
    bars_by_tf = {"1d": bars}
    _, feature_rows = build_price_feature_matrix(bars)
    validated_params = {
        "feature_mode": "prices_only",
        "label_horizon": 5,
        "train_bars": 120,
        "test_bars": 60,
        "step_bars": 60,
        "label_mode": "binary",
        "label_threshold": 0.01,
        "label_method": "endpoint",
    }

    result = await build_data_preview(
        AsyncMock(),
        bars_by_timeframe=bars_by_tf,
        decision_timeframe="1d",
        validated_params=validated_params,
        macro_series_ids=[],
        fundamental_metrics=[],
        context_warnings=[],
        strategy_warnings=[],
        bars=bars,
        feature_rows=feature_rows,
    )

    readiness = result["walk_forward_readiness"]
    assert readiness["valid_feature_rows"] > 0
    assert readiness["trainable_rows"] > 0
    assert readiness["structural_folds"] > 0
    assert "viable_folds" in readiness


@pytest.mark.asyncio
async def test_build_data_preview_meta_label_uses_validated_params():
    bars = _sample_bars(300)
    bars_by_tf = {"1h": bars}
    validated_params = {
        "feature_mode": "prices_only",
        "label_horizon": 5,
        "train_bars": 120,
        "test_bars": 60,
        "step_bars": 60,
        "label_mode": "meta_label",
        "label_threshold": 0.01,
        "label_method": "endpoint",
        "base_strategy_id": "crypto_trend_entry",
        "base_strategy_params": {"slow_period": 50, "rsi_period": 14, "rsi_max": 65},
        "profit_atr_mult": 2.0,
        "stop_atr_mult": 1.5,
        "max_horizon_bars": 48,
    }

    result = await build_data_preview(
        AsyncMock(),
        bars_by_timeframe=bars_by_tf,
        decision_timeframe="1h",
        validated_params=validated_params,
        macro_series_ids=[],
        fundamental_metrics=[],
        context_warnings=[],
        strategy_warnings=[],
    )

    assert result["label_preview"]["label_mode"] == "meta_label"
    assert sum(result["label_preview"]["class_distribution"].values()) >= 0


@pytest.mark.asyncio
async def test_build_data_preview_warns_when_all_features_null():
    bars = _sample_bars(120)
    bars_by_tf = {"1d": bars}
    validated_params = {
        "feature_mode": "prices_only",
        "label_horizon": 5,
        "train_bars": 60,
        "test_bars": 30,
        "step_bars": 30,
        "label_mode": "binary",
        "label_threshold": 0.01,
        "label_method": "endpoint",
    }

    result = await build_data_preview(
        AsyncMock(),
        bars_by_timeframe=bars_by_tf,
        decision_timeframe="1d",
        validated_params=validated_params,
        macro_series_ids=[],
        fundamental_metrics=[],
        context_warnings=[],
        strategy_warnings=[],
        bars=bars,
        feature_rows=[None] * len(bars),
    )

    assert result["walk_forward_readiness"]["valid_feature_rows"] == 0
    assert result["walk_forward_readiness"]["viable_folds"] == 0
    assert any("No valid feature rows" in warning for warning in result["warnings"])


@pytest.mark.asyncio
async def test_resolve_preview_warnings_skips_macro_for_prices_only():
    bars_by_tf = {"1d": _sample_bars()}
    validated_params = {"feature_mode": "prices_only", "label_horizon": 5}

    with patch.object(
        orchestrator,
        "resolve_macro_series_ids",
        new=AsyncMock(return_value=(["DFF"], ["macro warning"])),
    ) as mock_resolve:
        result = await orchestrator._resolve_preview_warnings(
            AsyncMock(),
            instrument_id=1,
            validated_params=validated_params,
            timeframe="1d",
            bars_by_tf=bars_by_tf,
        )

    mock_resolve.assert_not_awaited()
    assert result[0] == []
    assert result[1] == []


@pytest.mark.asyncio
async def test_preview_builds_feature_matrix_and_readiness():
    bars = _sample_bars(300)
    _, feature_rows = build_price_feature_matrix(bars)
    preview_payload = {
        "decision_timeframe": "1d",
        "bar_counts": {"1d": len(bars)},
        "warmup_bars_excluded": 50,
        "macro_coverage": [],
        "fundamental_metrics": [],
        "context_timeframes": [],
        "strategy_feature_ids": [],
        "label_preview": {"class_distribution": {"0": 10, "1": 12}},
        "walk_forward_readiness": {"viable_folds": 2, "valid_feature_rows": 200},
        "warnings": [],
    }

    with (
        patch.object(
            orchestrator,
            "validate_ml_params",
            return_value={
                "feature_mode": "prices_only",
                "label_horizon": 5,
                "train_bars": 120,
                "test_bars": 60,
                "step_bars": 60,
            },
        ),
        patch.object(
            orchestrator.instrument_dal,
            "get_by_symbol",
            new=AsyncMock(return_value={"id": 1, "symbol": "AAPL"}),
        ),
        patch.object(
            orchestrator,
            "_load_bars_and_features",
            new=AsyncMock(
                return_value=(
                    bars,
                    ["feat_a"],
                    feature_rows,
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                ),
            ),
        ) as mock_load,
        patch.object(
            orchestrator,
            "_load_bars_by_timeframe",
            new=AsyncMock(return_value={"1d": bars}),
        ),
        patch.object(
            orchestrator,
            "build_data_preview",
            new=AsyncMock(return_value=preview_payload),
        ) as mock_preview,
    ):
        result = await orchestrator.preview_ml_data_for_symbol(
            AsyncMock(),
            symbol="AAPL",
            params={},
            timeframe="1d",
            start=None,
            end=None,
        )

    assert result == preview_payload
    mock_load.assert_awaited_once()
    mock_preview.assert_awaited_once()
    call_kwargs = mock_preview.await_args.kwargs
    assert call_kwargs["bars"] is bars
    assert call_kwargs["feature_rows"] is feature_rows
