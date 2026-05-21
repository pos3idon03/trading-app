from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from features.tiingo.crypto_client import fetch_crypto_bars


@pytest.mark.asyncio
async def test_fetch_crypto_bars_daily():
    payload = [{
        "ticker": "btcusd",
        "priceData": [{
            "date": "2024-01-15T00:00:00Z",
            "open": 42000,
            "high": 43000,
            "low": 41000,
            "close": 42500,
            "volume": 100,
        }],
    }]
    with patch("features.tiingo.crypto_client.get_token", return_value="tok"), patch(
        "features.tiingo.crypto_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        records = await fetch_crypto_bars("BTC-USD", 1, "1d", start, end)

    assert len(records) == 1
    assert records[0].timeframe == "1d"
    assert records[0].source == "tiingo_crypto"
    params = instance.get.await_args.kwargs["params"]
    assert params["resampleFreq"] == "1Day"
    assert params["startDate"] == "2024-01-01"
    assert params["endDate"] == "2024-01-31"


@pytest.mark.asyncio
async def test_fetch_crypto_bars_historical_omits_end_date():
    payload = [{"ticker": "btcusd", "priceData": []}]
    with patch("features.tiingo.crypto_client.get_token", return_value="tok"), patch(
        "features.tiingo.crypto_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        start = datetime(2010, 1, 1, tzinfo=timezone.utc)
        await fetch_crypto_bars("BTC-USD", 1, "1d", start, None)

    params = instance.get.await_args.kwargs["params"]
    assert params["startDate"] == "2010-01-01"
    assert "endDate" not in params


@pytest.mark.asyncio
async def test_fetch_crypto_bars_4h_aggregates_hourly():
    payload = [{
        "ticker": "btcusd",
        "priceData": [
            {
                "date": "2024-01-01T00:00:00Z",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1,
            },
            {
                "date": "2024-01-01T01:00:00Z",
                "open": 101,
                "high": 102,
                "low": 100,
                "close": 101,
                "volume": 2,
            },
        ],
    }]
    with patch("features.tiingo.crypto_client.get_token", return_value="tok"), patch(
        "features.tiingo.crypto_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        records = await fetch_crypto_bars("btcusd", 1, "4h", start, end)

    assert len(records) == 1
    assert records[0].timeframe == "4h"
    params = instance.get.await_args.kwargs["params"]
    assert params["resampleFreq"] == "60min"
