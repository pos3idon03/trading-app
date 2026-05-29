from typing import Any

from features.agents.macro_crew.gemini_client import generate_text
from features.agents.macro_crew.prompts import build_forecaster_prompt


async def forecast_macro_outlook(context: dict[str, Any], analyst_text: str) -> str:
    prompt = build_forecaster_prompt(context, analyst_text)
    return await generate_text(prompt)
