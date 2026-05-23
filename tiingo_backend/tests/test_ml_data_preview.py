from unittest.mock import AsyncMock, patch

import pytest

from features.ml import orchestrator
from features.ml.data_preview import build_data_preview


def _sample_bars(count: int = 60) -> list[dict]:
    return [{"time": f"2024-01-{idx:02d}", "close": float(idx)} for idx in range(1, count + 1)]


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
async def test_preview_skips_full_feature_matrix():
    preview_payload = {
        "decision_timeframe": "1d",
        "bar_counts": {"1d": 100},
        "warmup_bars_excluded": 50,
        "macro_coverage": [],
        "fundamental_metrics": [],
        "context_timeframes": [],
        "strategy_feature_ids": [],
        "label_preview": {"class_distribution": {}},
        "warnings": [],
    }
    bars_by_tf = {"1d": [{"time": "2024-01-01", "close": 1.0}]}

    with (
        patch.object(orchestrator, "validate_ml_params", return_value={"feature_mode": "prices_only", "label_horizon": 5}),
        patch.object(orchestrator.instrument_dal, "get_by_symbol", new=AsyncMock(return_value={"id": 1, "symbol": "AAPL"})),
        patch.object(orchestrator, "_load_bars_by_timeframe", new=AsyncMock(return_value=bars_by_tf)),
        patch.object(orchestrator, "_resolve_preview_warnings", new=AsyncMock(return_value=([], [], [], [], [], []))),
        patch.object(orchestrator, "build_data_preview", new=AsyncMock(return_value=preview_payload)) as mock_preview,
        patch.object(orchestrator, "build_ml_feature_matrix", new=AsyncMock()) as mock_features,
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
    mock_features.assert_not_called()
    mock_preview.assert_awaited_once()
