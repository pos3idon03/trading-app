import json
from enum import Enum
from typing import Any


class MacroCyclePhase(str, Enum):
    EXPANSION = "Expansion"
    PEAK = "Peak"
    SLOWDOWN = "Slowdown"
    RECESSION = "Recession"
    TROUGH = "Trough"
    STAGNATION = "Stagnation"


def _normalize_phase(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for phase in MacroCyclePhase:
        if text.lower() == phase.value.lower():
            return phase.value
    return None


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def parse_cycle_phase_json(raw_text: str) -> dict[str, Any]:
    payload = json.loads(_extract_json_text(raw_text))
    return {
        "situation_phase": _normalize_phase(payload.get("situation_phase")),
        "outlook_phase": _normalize_phase(payload.get("outlook_phase")),
        "rationale": str(payload.get("rationale") or ""),
    }
