import json
from unittest.mock import AsyncMock, patch

import pytest

from features.agents.macro_crew.cycle_phase_classifier import classify_macro_cycle_phases


@pytest.mark.asyncio
async def test_classify_macro_cycle_phases_parses_response():
    context = {"as_of": "2024-06-01", "series": []}
    raw = json.dumps({
        "situation_phase": "Expansion",
        "outlook_phase": "Peak",
        "rationale": "Strong growth.",
    })
    with patch(
        "features.agents.macro_crew.cycle_phase_classifier.generate_text",
        new=AsyncMock(return_value=raw),
    ):
        situation_phase, outlook_phase = await classify_macro_cycle_phases(
            context,
            "Growth is steady.",
            "Momentum may peak.",
        )

    assert situation_phase == "Expansion"
    assert outlook_phase == "Peak"


@pytest.mark.asyncio
async def test_classify_macro_cycle_phases_returns_none_on_bad_json():
    with patch(
        "features.agents.macro_crew.cycle_phase_classifier.generate_text",
        new=AsyncMock(return_value="not valid json"),
    ):
        situation_phase, outlook_phase = await classify_macro_cycle_phases({}, "a", "b")

    assert situation_phase is None
    assert outlook_phase is None
