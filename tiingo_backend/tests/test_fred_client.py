from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from features.fred import fred_client


def _fred_payload(dates_values: list[tuple[str, str]]) -> dict:
    return {
        "observations": [{"date": d, "value": v} for d, v in dates_values],
    }


@pytest.mark.asyncio
async def test_fetch_all_observations_paginates():
    page1 = _fred_payload([(f"1990-01-{i:02d}", "1.0") for i in range(1, 11)])
    page2 = _fred_payload([("1990-01-11", "2.0")])

    with patch("features.fred.fred_client._api_key", return_value="key"), patch(
        "features.fred.fred_client.httpx.AsyncClient",
    ) as mock_client, patch("features.fred.fred_client.PAGE_SIZE", 10):
        instance = mock_client.return_value.__aenter__.return_value
        resp1 = MagicMock()
        resp1.json.return_value = page1
        resp2 = MagicMock()
        resp2.json.return_value = page2
        instance.get = AsyncMock(side_effect=[resp1, resp2])

        rows = await fred_client.fetch_all_observations("DGS10")

    assert len(rows) == 11
    assert rows[0]["obs_date"] == date(1990, 1, 1)
    assert rows[-1]["obs_date"] == date(1990, 1, 11)
    assert instance.get.await_count == 2
    second_call_params = instance.get.await_args_list[1].kwargs["params"]
    assert second_call_params["offset"] == 10


@pytest.mark.asyncio
async def test_fetch_observations_since_passes_start():
    payload = _fred_payload([("2024-06-01", "4.5")])

    with patch("features.fred.fred_client._api_key", return_value="key"), patch(
        "features.fred.fred_client.httpx.AsyncClient",
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        rows = await fred_client.fetch_observations_since("DGS10", date(2024, 6, 1))

    assert len(rows) == 1
    call_params = instance.get.await_args.kwargs["params"]
    assert call_params["observation_start"] == "2024-06-01"


@pytest.mark.asyncio
async def test_fetch_all_observations_continues_when_page_has_missing_values():
    """Pagination must use raw FRED row count, not parsed count after skipping '.'."""
    page1 = _fred_payload(
        [(f"1990-01-{i:02d}", "1.0") for i in range(1, 9)]
        + [(f"1990-01-{i:02d}", ".") for i in range(9, 11)],
    )
    page2 = _fred_payload([("1990-01-11", "2.0")])

    with patch("features.fred.fred_client._api_key", return_value="key"), patch(
        "features.fred.fred_client.httpx.AsyncClient",
    ) as mock_client, patch("features.fred.fred_client.PAGE_SIZE", 10):
        instance = mock_client.return_value.__aenter__.return_value
        resp1 = MagicMock()
        resp1.json.return_value = page1
        resp2 = MagicMock()
        resp2.json.return_value = page2
        instance.get = AsyncMock(side_effect=[resp1, resp2])

        rows = await fred_client.fetch_all_observations("T10Y2Y")

    assert len(rows) == 9
    assert rows[-1]["obs_date"] == date(1990, 1, 11)
    assert instance.get.await_count == 2


@pytest.mark.asyncio
async def test_parse_skips_missing_values():
    payload = _fred_payload([("2024-01-01", "."), ("2024-01-02", "3.0")])

    with patch("features.fred.fred_client._api_key", return_value="key"), patch(
        "features.fred.fred_client.httpx.AsyncClient",
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        rows = await fred_client.fetch_observations("DGS10", limit=100)

    assert len(rows) == 1
    assert rows[0]["value"] == 3.0
