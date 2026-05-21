from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from features.tiingo.eod_client import _pick_adjusted_price, fetch_eod_bars


class TestPickAdjustedPrice:
    def test_uses_adjusted_when_present(self):
        row = {
            "open": 500.0,
            "adjOpen": 125.0,
            "high": 510.0,
            "adjHigh": 127.5,
            "low": 490.0,
            "adjLow": 122.5,
            "close": 505.0,
            "adjClose": 126.25,
        }
        assert _pick_adjusted_price(row, "open") == 125.0
        assert _pick_adjusted_price(row, "close") == 126.25

    def test_falls_back_to_raw_when_adjusted_missing(self):
        row = {"open": 100.0, "close": 101.0}
        assert _pick_adjusted_price(row, "open") == 100.0


@pytest.mark.asyncio
async def test_fetch_eod_bars_stores_adjusted_prices():
    payload = [{
        "date": "2020-08-31T00:00:00.000Z",
        "open": 504.0,
        "high": 515.0,
        "low": 495.0,
        "close": 129.0,
        "adjOpen": 126.0,
        "adjHigh": 128.75,
        "adjLow": 123.75,
        "adjClose": 129.0,
        "volume": 1000000,
    }]
    start = datetime(2020, 8, 1, tzinfo=timezone.utc)
    end = datetime(2020, 9, 1, tzinfo=timezone.utc)

    with patch("features.tiingo.eod_client.get_token", return_value="tok"), patch(
        "features.tiingo.eod_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = AsyncMock()
        resp.json.return_value = payload
        resp.raise_for_status = AsyncMock()
        instance.get = AsyncMock(return_value=resp)

        records = await fetch_eod_bars("AAPL", 1, start, end)

    assert len(records) == 1
    assert records[0].open == 126.0
    assert records[0].high == 128.75
    assert records[0].close == 129.0
    assert records[0].source == "tiingo_eod"
