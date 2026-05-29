from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from features.agents.macro_crew.macro_crew_orchestrator import (
    generate_and_store_macro_brief,
    get_stored_macro_brief,
)


def _sample_overview() -> dict:
    return {
        "category": "all",
        "as_of": date(2024, 6, 1),
        "rows": [{
            "series_id": "UNRATE",
            "title": "Unemployment Rate",
            "category": "labor",
            "frequency": "Monthly",
            "change_1m": 0.1,
            "change_3m": 0.2,
            "change_6m": 0.3,
            "change_ytd": 0.4,
            "ma50_position": "Above",
            "ma200_position": "Below",
        }],
    }


def _stored_row(**overrides) -> dict:
    base = {
        "id": 1,
        "as_of": date(2024, 6, 1),
        "situation": "Current macro backdrop.",
        "outlook": "Near-term outlook.",
        "situation_phase": "Expansion",
        "outlook_phase": "Slowdown",
        "data_fingerprint": "fp-1",
        "model_name": "gemini-2.5-flash",
        "generated_at": datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_get_stored_macro_brief_returns_unavailable_when_empty():
    with patch(
        "features.agents.macro_crew.macro_crew_orchestrator.macro_brief_dal.get_latest_brief",
        new=AsyncMock(return_value=None),
    ):
        result = await get_stored_macro_brief(AsyncMock())

    assert result["available"] is False
    assert "No macro brief stored" in (result["message"] or "")


@pytest.mark.asyncio
async def test_get_stored_macro_brief_returns_latest_without_gemini():
    with patch(
        "features.agents.macro_crew.macro_crew_orchestrator.macro_brief_dal.get_latest_brief",
        new=AsyncMock(return_value=_stored_row()),
    ), patch(
        "features.agents.macro_crew.macro_analyst.generate_text",
        new=AsyncMock(),
    ) as analyst_mock:
        result = await get_stored_macro_brief(AsyncMock())

    assert result["available"] is True
    assert result["situation"] == "Current macro backdrop."
    assert result["situation_phase"] == "Expansion"
    assert result["outlook_phase"] == "Slowdown"
    analyst_mock.assert_not_called()


@pytest.mark.asyncio
async def test_generate_and_store_macro_brief_unavailable_without_api_key():
    with patch(
        "features.agents.macro_crew.macro_crew_orchestrator.load_macro_overview",
        new=AsyncMock(return_value=_sample_overview()),
    ), patch(
        "features.agents.macro_crew.macro_crew_orchestrator.get_settings",
    ) as mock_settings:
        settings = mock_settings.return_value
        settings.macro_brief_enabled = True
        settings.gemini_api_key = ""

        result = await generate_and_store_macro_brief(AsyncMock())

    assert result["available"] is False
    assert "GEMINI_API_KEY" in (result["message"] or "")


@pytest.mark.asyncio
async def test_generate_and_store_macro_brief_skips_gemini_when_fingerprint_exists():
    with patch(
        "features.agents.macro_crew.macro_crew_orchestrator.load_macro_overview",
        new=AsyncMock(return_value=_sample_overview()),
    ), patch(
        "features.agents.macro_crew.macro_crew_orchestrator.get_settings",
    ) as mock_settings, patch(
        "features.agents.macro_crew.macro_crew_orchestrator.macro_brief_dal.find_brief_by_fingerprint",
        new=AsyncMock(return_value=_stored_row()),
    ), patch(
        "features.agents.macro_crew.macro_analyst.generate_text",
        new=AsyncMock(),
    ) as analyst_mock:
        settings = mock_settings.return_value
        settings.macro_brief_enabled = True
        settings.gemini_api_key = "test-key"

        result = await generate_and_store_macro_brief(AsyncMock())

    assert result["available"] is True
    analyst_mock.assert_not_called()


@pytest.mark.asyncio
async def test_generate_and_store_macro_brief_runs_crew_and_persists():
    session = AsyncMock()
    session.commit = AsyncMock()

    with patch(
        "features.agents.macro_crew.macro_crew_orchestrator.load_macro_overview",
        new=AsyncMock(return_value=_sample_overview()),
    ), patch(
        "features.agents.macro_crew.macro_crew_orchestrator.get_settings",
    ) as mock_settings, patch(
        "features.agents.macro_crew.macro_crew_orchestrator.macro_brief_dal.find_brief_by_fingerprint",
        new=AsyncMock(return_value=None),
    ), patch(
        "features.agents.macro_crew.macro_analyst.generate_text",
        new=AsyncMock(return_value="Current macro backdrop."),
    ), patch(
        "features.agents.macro_crew.outlook_forecaster.generate_text",
        new=AsyncMock(return_value="Near-term outlook."),
    ), patch(
        "features.agents.macro_crew.cycle_phase_classifier.generate_text",
        new=AsyncMock(return_value='{"situation_phase":"Expansion","outlook_phase":"Slowdown"}'),
    ), patch(
        "features.agents.macro_crew.macro_crew_orchestrator.macro_brief_dal.insert_brief",
        new=AsyncMock(return_value=_stored_row()),
    ) as insert_mock:
        settings = mock_settings.return_value
        settings.macro_brief_enabled = True
        settings.gemini_api_key = "test-key"
        settings.macro_brief_model = "gemini-2.5-flash"

        result = await generate_and_store_macro_brief(session)

    assert result["available"] is True
    insert_mock.assert_awaited_once()
    insert_kwargs = insert_mock.await_args.kwargs
    assert insert_kwargs["situation_phase"] == "Expansion"
    assert insert_kwargs["outlook_phase"] == "Slowdown"
    session.commit.assert_awaited_once()
