import json
import logging
from typing import Any

from dtos.macro_cycle_dto import parse_cycle_phase_json
from features.agents.macro_crew.gemini_client import generate_text
from features.agents.macro_crew.prompts import build_cycle_classifier_prompt

logger = logging.getLogger(__name__)


async def classify_macro_cycle_phases(
    context: dict[str, Any],
    situation: str,
    outlook: str,
) -> tuple[str | None, str | None]:
    prompt = build_cycle_classifier_prompt(context, situation, outlook)
    raw = await generate_text(prompt)
    try:
        parsed = parse_cycle_phase_json(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("macro_cycle_phase_parse_failed", extra={"error": str(exc)})
        return None, None
    return parsed.get("situation_phase"), parsed.get("outlook_phase")
