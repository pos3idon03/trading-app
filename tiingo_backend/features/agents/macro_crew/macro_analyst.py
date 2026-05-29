from typing import Any

from features.agents.macro_crew.gemini_client import generate_text
from features.agents.macro_crew.prompts import build_analyst_prompt


async def analyze_macro_situation(context: dict[str, Any]) -> str:
    prompt = build_analyst_prompt(context)
    return await generate_text(prompt)
