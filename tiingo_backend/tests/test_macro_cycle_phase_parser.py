import json

import pytest

from dtos.macro_cycle_dto import MacroCyclePhase, parse_cycle_phase_json


def test_parse_cycle_phase_json_valid():
    raw = json.dumps({
        "situation_phase": "Expansion",
        "outlook_phase": "Slowdown",
        "rationale": "Growth is broad but decelerating.",
    })
    parsed = parse_cycle_phase_json(raw)
    assert parsed["situation_phase"] == MacroCyclePhase.EXPANSION.value
    assert parsed["outlook_phase"] == MacroCyclePhase.SLOWDOWN.value
    assert "Growth" in parsed["rationale"]


def test_parse_cycle_phase_json_fenced():
    raw = """```json
{
  "situation_phase": "Peak",
  "outlook_phase": "Recession",
  "rationale": "Late cycle."
}
```"""
    parsed = parse_cycle_phase_json(raw)
    assert parsed["situation_phase"] == "Peak"
    assert parsed["outlook_phase"] == "Recession"


def test_parse_cycle_phase_json_case_insensitive():
    raw = json.dumps({
        "situation_phase": "trough",
        "outlook_phase": "STAGNATION",
    })
    parsed = parse_cycle_phase_json(raw)
    assert parsed["situation_phase"] == "Trough"
    assert parsed["outlook_phase"] == "Stagnation"


def test_parse_cycle_phase_json_invalid_labels_become_none():
    raw = json.dumps({
        "situation_phase": "Boom",
        "outlook_phase": "Slowdown",
    })
    parsed = parse_cycle_phase_json(raw)
    assert parsed["situation_phase"] is None
    assert parsed["outlook_phase"] == "Slowdown"


def test_parse_cycle_phase_json_missing_fields():
    raw = json.dumps({"situation_phase": "Expansion"})
    parsed = parse_cycle_phase_json(raw)
    assert parsed["situation_phase"] == "Expansion"
    assert parsed["outlook_phase"] is None


def test_parse_cycle_phase_json_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_cycle_phase_json("not json")
