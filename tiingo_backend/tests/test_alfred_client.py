from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from features.fred.alfred_client import _collapse_initial_releases


def test_collapse_initial_releases_keeps_earliest_vintage():
    rows = [
        {"series_id": "CPI", "obs_date": date(2024, 1, 31), "value": 100.0, "release_date": date(2024, 2, 28)},
        {"series_id": "CPI", "obs_date": date(2024, 1, 31), "value": 100.5, "release_date": date(2024, 3, 15)},
    ]
    collapsed = _collapse_initial_releases(rows)
    assert len(collapsed) == 1
    assert collapsed[0]["release_date"] == date(2024, 2, 28)
    assert collapsed[0]["value"] == 100.0


@pytest.mark.asyncio
async def test_fetch_initial_release_observations():
    vintage_page = [
        {
            "date": "2024-01-31",
            "value": "100.0",
            "realtime_start": "2024-02-28",
            "realtime_end": "9999-12-31",
        },
    ]
    with patch(
        "features.fred.alfred_client._fetch_vintage_page",
        new=AsyncMock(return_value=([
            {
                "series_id": "CPIAUCSL",
                "obs_date": date(2024, 1, 31),
                "value": 100.0,
                "release_date": date(2024, 2, 28),
            },
        ], 1)),
    ), patch(
        "features.fred.alfred_client.get_settings",
        return_value=type("Settings", (), {"fred_api_key": "test-key"})(),
    ):
        from features.fred.alfred_client import fetch_initial_release_observations

        rows = await fetch_initial_release_observations("CPIAUCSL")
        assert rows[0]["release_date"] == date(2024, 2, 28)
