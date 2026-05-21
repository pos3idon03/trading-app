from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from features.tiingo import crypto_meta_client


@pytest.fixture(autouse=True)
def _clear_cache():
    crypto_meta_client.clear_crypto_meta_cache()
    yield
    crypto_meta_client.clear_crypto_meta_cache()


@pytest.mark.asyncio
async def test_get_crypto_meta_fetches_and_caches():
    payload = [{"ticker": "btcusd", "baseCurrency": "btc", "quoteCurrency": "usd"}]
    with patch("features.tiingo.crypto_meta_client.get_token", return_value="tok"), patch(
        "features.tiingo.crypto_meta_client.check_and_increment",
        new=AsyncMock(),
    ) as mock_rate, patch(
        "features.tiingo.crypto_meta_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        first = await crypto_meta_client.get_crypto_meta(AsyncMock())
        second = await crypto_meta_client.get_crypto_meta(AsyncMock())

    assert first == payload
    assert second == payload
    assert instance.get.await_count == 1
    mock_rate.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_crypto_meta_refreshes_after_ttl():
    payload = [{"ticker": "btcusd"}]
    crypto_meta_client._cache_rows = payload
    crypto_meta_client._cache_fetched_at = datetime(2000, 1, 1, tzinfo=timezone.utc)

    with patch("features.tiingo.crypto_meta_client.get_token", return_value="tok"), patch(
        "features.tiingo.crypto_meta_client.check_and_increment",
        new=AsyncMock(),
    ), patch(
        "features.tiingo.crypto_meta_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = [{"ticker": "ethusd"}]
        instance.get = AsyncMock(return_value=resp)

        rows = await crypto_meta_client.get_crypto_meta(AsyncMock())

    assert rows == [{"ticker": "ethusd"}]
    assert instance.get.await_count == 1
