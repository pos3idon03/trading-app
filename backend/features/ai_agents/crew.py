"""CrewAI crew assembly and orchestration for the trading intelligence system.

The crew runs three specialist agents in parallel (fundamental, macro, sentiment)
and then the manager agent synthesizes their outputs into a structured trading signal.
"""
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crewai import Crew, Process

from features.ai_agents.agent_definitions import (
    build_fundamental_agent,
    build_macro_agent,
    build_manager_agent,
    build_sentiment_agent,
)
from features.ai_agents.llm_provider import get_llm_for_crew, resolve_model_chain
from features.ai_agents.tasks import (
    build_fundamental_task,
    build_macro_task,
    build_sentiment_task,
    build_synthesis_task,
)
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TradingSignal:
    asset: str
    bias: str
    conviction_score: float
    fundamental_summary: str
    macro_summary: str
    macro_score: float
    sentiment_score: float
    reasoning: str
    key_risk: str
    timestamp: str
    raw_output: str = field(default="", repr=False)
    fundamental_report: str = field(default="", repr=False)
    macro_report: str = field(default="", repr=False)
    sentiment_report: str = field(default="", repr=False)
    duration_ms: int = 0
    provider_used: str = ""


def run_analysis_crew(ticker: str, llm: str = "gpt-4o-mini") -> TradingSignal:
    """Assemble and run the full multi-agent research crew for a given ticker.

    Returns a structured TradingSignal with the manager's synthesis and
    individual agent reports for traceability.
    """
    t0 = time.perf_counter()
    primary, fallback = resolve_model_chain(llm)
    logger.info("crew_start", ticker=ticker, llm=llm, primary=primary, fallback=fallback)

    resolved_llm: str = get_llm_for_crew(llm)

    fundamental_agent = build_fundamental_agent(resolved_llm)
    macro_agent = build_macro_agent(resolved_llm)
    sentiment_agent = build_sentiment_agent(resolved_llm)
    manager_agent = build_manager_agent(resolved_llm)

    fundamental_task = build_fundamental_task(fundamental_agent, ticker)
    macro_task = build_macro_task(macro_agent, ticker)
    sentiment_task = build_sentiment_task(sentiment_agent, ticker)
    synthesis_task = build_synthesis_task(
        manager_agent,
        ticker,
        context_tasks=[fundamental_task, macro_task, sentiment_task],
    )

    crew = Crew(
        agents=[fundamental_agent, macro_agent, sentiment_agent, manager_agent],
        tasks=[fundamental_task, macro_task, sentiment_task, synthesis_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff(inputs={"ticker": ticker})

    duration_ms = int((time.perf_counter() - t0) * 1000)
    logger.info("crew_complete", ticker=ticker, duration_ms=duration_ms)

    raw_output = str(result)
    signal = _parse_signal(raw_output, ticker)
    signal.raw_output = raw_output
    signal.duration_ms = duration_ms
    signal.provider_used = primary

    signal.fundamental_report = _extract_task_output(fundamental_task)
    signal.macro_report = _extract_task_output(macro_task)
    signal.sentiment_report = _extract_task_output(sentiment_task)

    return signal


def _parse_signal(raw_output: str, ticker: str) -> TradingSignal:
    """Extract the JSON trading signal from the manager's raw text output."""
    json_match = re.search(r"\{[^{}]*\"bias\"\s*:[^{}]*\}", raw_output, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return _signal_from_dict(data, ticker)
        except json.JSONDecodeError:
            pass

    logger.warning("signal_parse_failed_using_defaults", ticker=ticker)
    return _default_signal(ticker, raw_output)


def _signal_from_dict(data: dict, ticker: str) -> TradingSignal:
    return TradingSignal(
        asset=data.get("asset", ticker),
        bias=data.get("bias", "neutral"),
        conviction_score=float(data.get("conviction_score", 0.5)),
        fundamental_summary=data.get("fundamental_summary", ""),
        macro_summary=data.get("macro_summary", ""),
        macro_score=float(data.get("macro_score", 0.0)),
        sentiment_score=float(data.get("sentiment_score", 0.0)),
        reasoning=data.get("reasoning", ""),
        key_risk=data.get("key_risk", ""),
        timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )


def _default_signal(ticker: str, raw_output: str) -> TradingSignal:
    return TradingSignal(
        asset=ticker,
        bias="neutral",
        conviction_score=0.0,
        fundamental_summary="Parsing failed — see raw_output.",
        macro_summary="",
        macro_score=0.0,
        sentiment_score=0.0,
        reasoning=raw_output[:500],
        key_risk="Signal parsing failed; manual review required.",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _extract_task_output(task) -> str:
    """Safely extract the output string from a completed CrewAI task."""
    try:
        output = task.output
        if output is None:
            return ""
        return str(output.raw) if hasattr(output, "raw") else str(output)
    except Exception:
        return ""
