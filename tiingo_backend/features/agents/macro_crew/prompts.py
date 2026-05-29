import json
from typing import Any


def build_analyst_prompt(context: dict[str, Any]) -> str:
    data = json.dumps(context, indent=2, default=str)
    return (
        "You are a Macro Analyst agent on a financial dashboard crew.\n"
        "Summarize the CURRENT macroeconomic situation using ONLY the data below.\n\n"
        "Each series includes period trends (Δ 1M/3M/6M/YTD as percent changes) and "
        "moving-average signals (Above/Below/At vs 50-period and 200-period MAs).\n\n"
        "Write 2-3 concise paragraphs covering growth, labor, inflation, rates, consumer, "
        "housing, energy, and goods themes. Highlight cross-category tensions and "
        "notable divergences. Do not invent data beyond what is provided.\n\n"
        f"Macro data as of {context.get('as_of', 'unknown')}:\n{data}"
    )


def build_forecaster_prompt(context: dict[str, Any], analyst_text: str) -> str:
    data = json.dumps(context, indent=2, default=str)
    return (
        "You are an Outlook Forecaster agent on a financial dashboard crew.\n"
        "Given the macro analyst summary and the underlying series data, describe "
        "near-term macro EXPECTATIONS implied by the trend direction and MA signals.\n\n"
        "Write 1-2 concise paragraphs on likely direction, key risks, and what to "
        "watch next. Be probabilistic when evidence is mixed. Do not invent data.\n\n"
        f"Analyst summary:\n{analyst_text}\n\n"
        f"Macro data as of {context.get('as_of', 'unknown')}:\n{data}"
    )


def build_cycle_classifier_prompt(
    context: dict[str, Any],
    analyst_text: str,
    forecaster_text: str,
) -> str:
    phases = "Expansion, Peak, Slowdown, Recession, Trough, Stagnation"
    data = json.dumps(context, indent=2, default=str)
    return (
        "You are a Cycle Phase Classifier agent on a financial dashboard crew.\n"
        "Given the macro analyst summary, outlook forecaster summary, and underlying "
        "series data, assign a business-cycle phase label for the CURRENT situation "
        "and a separate label for the NEAR-TERM outlook.\n\n"
        "Phase definitions:\n"
        "- Expansion: broad growth, improving labor, rising activity\n"
        "- Peak: late-cycle strength, overheating risks, policy tightening\n"
        "- Slowdown: decelerating growth, mixed signals, rising caution\n"
        "- Recession: contraction in activity, rising unemployment, demand weakness\n"
        "- Trough: cycle bottom, stabilization after contraction, early recovery signs\n"
        "- Stagnation: flat growth, persistent inflation/unemployment, low momentum\n\n"
        f"Allowed values (exact spelling): {phases}\n"
        "Pick exactly one label per field. outlook_phase may differ from situation_phase.\n\n"
        "Return ONLY valid JSON with this schema:\n"
        "{\n"
        '  "situation_phase": "Expansion|Peak|Slowdown|Recession|Trough|Stagnation",\n'
        '  "outlook_phase": "Expansion|Peak|Slowdown|Recession|Trough|Stagnation",\n'
        '  "rationale": "one short sentence"\n'
        "}\n\n"
        f"Analyst summary (current situation):\n{analyst_text}\n\n"
        f"Forecaster summary (near-term outlook):\n{forecaster_text}\n\n"
        f"Macro data as of {context.get('as_of', 'unknown')}:\n{data}"
    )
