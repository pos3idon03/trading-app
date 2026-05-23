from datetime import date, timedelta
from unittest.mock import patch

import pytest

from features.market_data.overview_macro import load_macro_overview


def _daily_obs(count: int, base: float = 100.0) -> list[dict]:
    start = date(2024, 1, 1)
    return [
        {"obs_date": start + timedelta(days=i), "value": base + i}
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_load_macro_overview_all_series():
    class FakeSession:
        pass

    async def fake_obs(session, series_id, limit=250, order="desc"):
        return list(reversed(_daily_obs(220, base=100.0)))

    with patch(
        "features.market_data.overview_macro.macro_dal.get_observations",
        side_effect=fake_obs,
    ):
        payload = await load_macro_overview(FakeSession(), "all")

    assert payload["category"] == "all"
    assert len(payload["rows"]) == 25
    first = payload["rows"][0]
    assert first["change_1m"] is not None
    assert first["ma50_position"] in {"Above", "Below", "At"}


@pytest.mark.asyncio
async def test_load_macro_overview_filters_category():
    class FakeSession:
        pass

    async def fake_obs(session, series_id, limit=250, order="desc"):
        return list(reversed(_daily_obs(60, base=50.0)))

    with patch(
        "features.market_data.overview_macro.macro_dal.get_observations",
        side_effect=fake_obs,
    ):
        payload = await load_macro_overview(FakeSession(), "inflation")

    assert all(row["category"] == "inflation" for row in payload["rows"])
    assert len(payload["rows"]) == 3


@pytest.mark.asyncio
async def test_load_macro_overview_filters_growth():
    class FakeSession:
        pass

    async def fake_obs(session, series_id, limit=250, order="desc"):
        return list(reversed(_daily_obs(60, base=50.0)))

    with patch(
        "features.market_data.overview_macro.macro_dal.get_observations",
        side_effect=fake_obs,
    ):
        payload = await load_macro_overview(FakeSession(), "growth")

    assert all(row["category"] == "growth" for row in payload["rows"])
    assert len(payload["rows"]) == 3


@pytest.mark.asyncio
async def test_load_macro_overview_filters_consumer():
    class FakeSession:
        pass

    async def fake_obs(session, series_id, limit=250, order="desc"):
        return list(reversed(_daily_obs(60, base=50.0)))

    with patch(
        "features.market_data.overview_macro.macro_dal.get_observations",
        side_effect=fake_obs,
    ):
        payload = await load_macro_overview(FakeSession(), "consumer")

    assert all(row["category"] == "consumer" for row in payload["rows"])
    assert len(payload["rows"]) == 3
