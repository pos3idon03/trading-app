from datetime import date, datetime, timezone
from typing import Any

from config import get_settings
from dal import macro_brief_dal
from features.agents.macro_crew.context_builder import build_macro_context, rows_fingerprint
from features.agents.macro_crew.cycle_phase_classifier import classify_macro_cycle_phases
from features.agents.macro_crew.macro_analyst import analyze_macro_situation
from features.agents.macro_crew.outlook_forecaster import forecast_macro_outlook
from features.market_data.overview_macro import load_macro_overview
from sqlalchemy.ext.asyncio import AsyncSession


def _unavailable(message: str, as_of: date | None = None) -> dict[str, Any]:
    return {
        "as_of": as_of,
        "situation": None,
        "outlook": None,
        "situation_phase": None,
        "outlook_phase": None,
        "generated_at": None,
        "available": False,
        "message": message,
    }


def _availability_error() -> str | None:
    settings = get_settings()
    if not settings.macro_brief_enabled:
        return "Macro brief is disabled"
    if not settings.gemini_api_key:
        return "GEMINI_API_KEY is not configured"
    return None


def _brief_payload(row: dict) -> dict[str, Any]:
    return {
        "as_of": row["as_of"],
        "situation": row["situation"],
        "outlook": row["outlook"],
        "situation_phase": row.get("situation_phase"),
        "outlook_phase": row.get("outlook_phase"),
        "generated_at": row["generated_at"],
        "available": True,
        "message": None,
    }


def _brief_job_result(payload: dict[str, Any]) -> dict[str, Any]:
    as_of = payload.get("as_of")
    generated_at = payload.get("generated_at")
    return {
        **payload,
        "as_of": as_of.isoformat() if isinstance(as_of, date) else as_of,
        "generated_at": generated_at.isoformat() if isinstance(generated_at, datetime) else generated_at,
    }


async def get_stored_macro_brief(session: AsyncSession) -> dict[str, Any]:
    row = await macro_brief_dal.get_latest_brief(session)
    if row is None:
        return _unavailable("No macro brief stored yet. Run macro refresh or backfill.")
    return _brief_payload(row)


async def generate_and_store_macro_brief(
    session: AsyncSession,
    *,
    for_job: bool = False,
) -> dict[str, Any]:
    overview = await load_macro_overview(session, "all")
    as_of = overview.get("as_of")

    error = _availability_error()
    if error:
        payload = _unavailable(error, as_of=as_of)
        return _brief_job_result(payload) if for_job else payload

    fingerprint = rows_fingerprint(overview)
    existing = await macro_brief_dal.find_brief_by_fingerprint(session, fingerprint)
    if existing:
        payload = _brief_payload(existing)
        return _brief_job_result(payload) if for_job else payload

    settings = get_settings()
    context = build_macro_context(overview)
    situation = await analyze_macro_situation(context)
    outlook = await forecast_macro_outlook(context, situation)
    situation_phase, outlook_phase = await classify_macro_cycle_phases(
        context,
        situation,
        outlook,
    )
    row = await macro_brief_dal.insert_brief(
        session,
        as_of=as_of,
        situation=situation,
        outlook=outlook,
        situation_phase=situation_phase,
        outlook_phase=outlook_phase,
        data_fingerprint=fingerprint,
        model_name=settings.macro_brief_model,
        generated_at=datetime.now(timezone.utc),
    )
    await session.commit()
    payload = _brief_payload(row)
    return _brief_job_result(payload) if for_job else payload
