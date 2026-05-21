from unittest.mock import AsyncMock, MagicMock, patch

import pytest

httpx = pytest.importorskip("httpx")

from dtos.market_data_dto import TickerSearchResponseDTO, TickerSearchResultDTO
from features.tiingo.search_client import map_asset_type, search_tickers, _parse_item


class TestMapAssetType:
    def test_stock(self):
        assert map_asset_type("Stock") == "stock"

    def test_etf(self):
        assert map_asset_type("ETF") == "etf"

    def test_mutual_fund(self):
        assert map_asset_type("Mutual Fund") == "mutual_fund"

    def test_crypto(self):
        assert map_asset_type("Crypto") == "crypto"


class TestParseItem:
    def test_apple(self):
        row = _parse_item({
            "ticker": "AAPL",
            "name": "Apple Inc",
            "assetType": "Stock",
            "exchange": "NASDAQ",
        })
        assert row is not None
        assert row.symbol == "AAPL"
        assert row.name == "Apple Inc"
        assert row.asset_type == "stock"
        assert row.tiingo_ticker == "AAPL"

    def test_missing_ticker(self):
        assert _parse_item({"name": "Foo"}) is None

    def test_crypto_btcusd(self):
        row = _parse_item({
            "ticker": "btcusd",
            "name": "Bitcoin USD",
            "assetType": "Crypto",
            "exchange": "GDAX",
        })
        assert row is not None
        assert row.symbol == "BTC-USD"
        assert row.asset_type == "crypto"
        assert row.tiingo_ticker == "btcusd"


@pytest.mark.asyncio
async def test_search_tickers_success():
    payload = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "assetType": "Stock",
            "exchange": "NASDAQ",
        }
    ]
    with patch("features.tiingo.search_client.get_token", return_value="tok"), patch(
        "features.tiingo.search_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        result = await search_tickers("Apple", limit=10)

    assert result.count == 1
    assert result.results[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_search_tickers_error_returns_empty():
    with patch("features.tiingo.search_client.get_token", return_value="tok"), patch(
        "features.tiingo.search_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.get = AsyncMock(side_effect=httpx.HTTPError("fail"))

        result = await search_tickers("Apple")

    assert result.count == 0
    assert result.results == []


@pytest.mark.asyncio
async def test_instrument_search_route():
    from httpx import ASGITransport, AsyncClient
    from main import app

    dto = TickerSearchResponseDTO(
        results=[
            TickerSearchResultDTO(
                symbol="AAPL",
                name="Apple Inc",
                asset_type="stock",
                exchange="NASDAQ",
                tiingo_ticker="AAPL",
            )
        ],
        count=1,
    )

    with patch("routes.instruments.search_tickers", new=AsyncMock(return_value=dto)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/instruments/search?query=Apple")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["symbol"] == "AAPL"
