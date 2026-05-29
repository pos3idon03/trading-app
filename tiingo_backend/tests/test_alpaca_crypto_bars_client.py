from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.alpaca.crypto_bars_client import fetch_crypto_bars


@pytest.mark.asyncio
async def test_fetch_crypto_bars_maps_symbol_and_timeframe():
    captured: dict = {}

    async def fake_get(url, *, headers, params):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        response = MagicMock()
        response.raise_for_status = lambda: None
        response.json.return_value = {
            "bars": {
                "BTC/USD": [
                    {
                        "t": "2026-05-29T14:00:00Z",
                        "o": 73500.0,
                        "h": 73600.0,
                        "l": 73400.0,
                        "c": 73550.0,
                        "v": 12,
                        "n": 100,
                        "vw": 73520.0,
                    }
                ]
            }
        }
        return response

    client = AsyncMock()
    client.get = fake_get
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "features.alpaca.crypto_bars_client.httpx.AsyncClient",
        return_value=client,
    ):
        records = await fetch_crypto_bars(
            "BTC-USD",
            10,
            "1h",
            datetime(2026, 5, 29, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 29, 15, 0, tzinfo=timezone.utc),
        )

    assert captured["params"]["symbols"] == "BTC/USD"
    assert captured["params"]["timeframe"] == "1Hour"
    assert captured["params"]["start"] == "2026-05-29T00:00:00Z"
    assert captured["params"]["end"] == "2026-05-29T15:00:00Z"
    assert len(records) == 1
    assert records[0].source == "alpaca_crypto"
    assert records[0].instrument_id == 10
    assert records[0].timeframe == "1h"
    assert records[0].close == 73550.0
