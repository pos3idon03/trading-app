from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from features.tiingo.iex_client import fetch_iex_bars


@pytest.mark.asyncio
async def test_fetch_iex_bars():
    payload = [{
        "date": "2024-01-15T10:00:00Z",
        "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000,
    }]
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 31, tzinfo=timezone.utc)

    with patch("features.tiingo.iex_client.get_token", return_value="tok"), patch(
        "features.tiingo.iex_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = AsyncMock()
        resp.json.return_value = payload
        resp.raise_for_status = AsyncMock()
        instance.get = AsyncMock(return_value=resp)

        records = await fetch_iex_bars("AAPL", 1, "5m", start, end)

    assert len(records) == 1
    assert records[0].source == "tiingo_iex"
