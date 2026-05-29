from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from dal import macro_brief_dal
from models.macro import MacroBrief


@pytest.mark.asyncio
async def test_insert_and_get_latest_brief():
    session = AsyncMock()
    row = MacroBrief(
        id=1,
        as_of=date(2024, 6, 1),
        situation="Growth steady.",
        outlook="Rates may stay elevated.",
        situation_phase="Expansion",
        outlook_phase="Peak",
        data_fingerprint="abc123",
        model_name="gemini-2.5-flash",
        generated_at=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
    )
    session.add = MagicMock()
    session.flush = AsyncMock()

    async def _flush_side_effect():
        session.add.call_args[0][0].id = row.id

    session.flush.side_effect = _flush_side_effect

    inserted = await macro_brief_dal.insert_brief(
        session,
        as_of=row.as_of,
        situation=row.situation,
        outlook=row.outlook,
        situation_phase=row.situation_phase,
        outlook_phase=row.outlook_phase,
        data_fingerprint=row.data_fingerprint,
        model_name=row.model_name,
        generated_at=row.generated_at,
    )

    assert inserted["situation"] == "Growth steady."
    assert inserted["situation_phase"] == "Expansion"
    assert inserted["outlook_phase"] == "Peak"
    assert inserted["data_fingerprint"] == "abc123"
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_latest_brief_returns_none_when_empty():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    latest = await macro_brief_dal.get_latest_brief(session)

    assert latest is None


@pytest.mark.asyncio
async def test_find_brief_by_fingerprint():
    session = AsyncMock()
    row = MacroBrief(
        id=2,
        as_of=date(2024, 6, 1),
        situation="Inflation cooling.",
        outlook="Soft landing likely.",
        data_fingerprint="fp-xyz",
        model_name="gemini-2.5-flash",
        generated_at=datetime(2024, 6, 2, 8, 0, tzinfo=timezone.utc),
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)

    found = await macro_brief_dal.find_brief_by_fingerprint(session, "fp-xyz")

    assert found is not None
    assert found["outlook"] == "Soft landing likely."
