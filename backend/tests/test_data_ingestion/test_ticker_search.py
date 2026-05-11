"""Tests for the ticker search feature and endpoint."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_quote(symbol: str, name: str, quote_type: str, exchange: str = "NMS") -> dict:
    return {
        "symbol": symbol,
        "longname": name,
        "quoteType": quote_type,
        "exchange": exchange,
    }


def _patch_yf_search(quotes: list[dict]):
    """Patch yfinance.Search so .quotes returns the given list."""
    mock_search_instance = MagicMock()
    mock_search_instance.quotes = quotes
    return patch(
        "features.data_ingestion.ticker_search._run_yfinance_search",
        return_value=quotes,
    )


# ---------------------------------------------------------------------------
# Feature: search_tickers
# ---------------------------------------------------------------------------

class TestSearchTickers:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [
            _make_quote("MSFT", "Microsoft Corporation", "EQUITY", "NMS"),
            _make_quote("MSTR", "MicroStrategy Incorporated", "EQUITY", "NMS"),
        ]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="Micro", limit=10)

        assert response.count == 2
        assert response.results[0].symbol == "MSFT"
        assert response.results[0].name == "Microsoft Corporation"
        assert response.results[0].asset_type == "stock"
        assert response.results[0].exchange == "NMS"

    @pytest.mark.asyncio
    async def test_maps_equity_to_stock(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("AAPL", "Apple Inc.", "EQUITY")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="Apple", limit=10)

        assert response.results[0].asset_type == "stock"

    @pytest.mark.asyncio
    async def test_maps_etf_type(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("SPY", "SPDR S&P 500 ETF", "ETF")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="SPY", limit=10)

        assert response.results[0].asset_type == "etf"

    @pytest.mark.asyncio
    async def test_maps_mutualfund_to_etf(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("VTSAX", "Vanguard Total Stock Market", "MUTUALFUND")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="Vanguard", limit=10)

        assert response.results[0].asset_type == "etf"

    @pytest.mark.asyncio
    async def test_maps_cryptocurrency_type(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("BTC-USD", "Bitcoin USD", "CRYPTOCURRENCY")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="Bitcoin", limit=10)

        assert response.results[0].asset_type == "crypto"

    @pytest.mark.asyncio
    async def test_maps_currency_to_forex(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("EURUSD=X", "EUR/USD", "CURRENCY")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="EUR", limit=10)

        assert response.results[0].asset_type == "forex"

    @pytest.mark.asyncio
    async def test_maps_index_type(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("^GSPC", "S&P 500", "INDEX")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="S&P", limit=10)

        assert response.results[0].asset_type == "index"

    @pytest.mark.asyncio
    async def test_maps_unknown_type_to_stock(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote("XYZ", "Unknown Asset", "EXOTIC")]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="XYZ", limit=10)

        assert response.results[0].asset_type == "stock"

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        from features.data_ingestion.ticker_search import search_tickers

        quotes = [_make_quote(f"SYM{i}", f"Company {i}", "EQUITY") for i in range(20)]
        with _patch_yf_search(quotes):
            response = await search_tickers(query="Company", limit=5)

        assert response.count == 5
        assert len(response.results) == 5

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        from features.data_ingestion.ticker_search import search_tickers

        with patch(
            "features.data_ingestion.ticker_search._run_yfinance_search",
            side_effect=Exception("network error"),
        ):
            response = await search_tickers(query="AAPL", limit=10)

        assert response.count == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_handles_empty_results(self):
        from features.data_ingestion.ticker_search import search_tickers

        with _patch_yf_search([]):
            response = await search_tickers(query="ZZZZ", limit=10)

        assert response.count == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_uses_shortname_when_longname_missing(self):
        from features.data_ingestion.ticker_search import search_tickers

        quote = {
            "symbol": "TST",
            "shortname": "Test Corp",
            "quoteType": "EQUITY",
            "exchange": "NMS",
        }
        with patch(
            "features.data_ingestion.ticker_search._run_yfinance_search",
            return_value=[quote],
        ):
            response = await search_tickers(query="Test", limit=10)

        assert response.results[0].name == "Test Corp"


# ---------------------------------------------------------------------------
# DTOs: TickerSearchResult / TickerSearchResponse
# ---------------------------------------------------------------------------

class TestTickerSearchDTOs:
    def test_ticker_search_result_defaults(self):
        from dtos.market_data_dto import TickerSearchResult

        result = TickerSearchResult(symbol="AAPL", name="Apple Inc.")
        assert result.asset_type == "stock"
        assert result.exchange is None

    def test_ticker_search_response_count(self):
        from dtos.market_data_dto import TickerSearchResult, TickerSearchResponse

        items = [
            TickerSearchResult(symbol="AAPL", name="Apple Inc."),
            TickerSearchResult(symbol="AMZN", name="Amazon.com Inc."),
        ]
        response = TickerSearchResponse(results=items, count=2)
        assert response.count == 2
        assert len(response.results) == 2


# ---------------------------------------------------------------------------
# Route: GET /tickers/search
# ---------------------------------------------------------------------------

class TestTickerSearchRoute:
    def _make_client(self):
        """Build a test client with a mocked DB session."""
        import os
        os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        os.environ.setdefault("DATABASE_SYNC_URL", "postgresql://test:test@localhost/test")

        from fastapi.testclient import TestClient
        from main import app

        return TestClient(app)

    def test_returns_200_with_results(self):
        from dtos.market_data_dto import TickerSearchResponse, TickerSearchResult

        mock_response = TickerSearchResponse(
            results=[
                TickerSearchResult(symbol="MSFT", name="Microsoft Corporation", exchange="NMS")
            ],
            count=1,
        )

        with patch(
            "routes.data_ingestion.search_tickers",
            new=AsyncMock(return_value=mock_response),
        ):
            client = self._make_client()
            response = client.get("/api/v1/data/tickers/search?query=Micro")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["symbol"] == "MSFT"

    def test_rejects_short_query(self):
        client = self._make_client()
        response = client.get("/api/v1/data/tickers/search?query=A")
        assert response.status_code == 422

    def test_missing_query_returns_422(self):
        client = self._make_client()
        response = client.get("/api/v1/data/tickers/search")
        assert response.status_code == 422

    def test_limit_defaults_to_ten(self):
        from dtos.market_data_dto import TickerSearchResponse

        mock_response = TickerSearchResponse(results=[], count=0)
        captured: dict = {}

        async def mock_search(query, limit):
            captured["limit"] = limit
            return mock_response

        with patch("routes.data_ingestion.search_tickers", new=mock_search):
            client = self._make_client()
            client.get("/api/v1/data/tickers/search?query=Apple")

        assert captured.get("limit") == 10

    def test_returns_all_asset_types(self):
        from dtos.market_data_dto import TickerSearchResponse, TickerSearchResult

        mock_response = TickerSearchResponse(
            results=[
                TickerSearchResult(symbol="BTC-USD", name="Bitcoin USD", asset_type="crypto"),
                TickerSearchResult(symbol="SPY", name="SPDR S&P 500 ETF", asset_type="etf"),
                TickerSearchResult(symbol="AAPL", name="Apple Inc.", asset_type="stock"),
            ],
            count=3,
        )

        with patch(
            "routes.data_ingestion.search_tickers",
            new=AsyncMock(return_value=mock_response),
        ):
            client = self._make_client()
            response = client.get("/api/v1/data/tickers/search?query=test")

        assert response.status_code == 200
        types = {r["asset_type"] for r in response.json()["results"]}
        assert types == {"crypto", "etf", "stock"}
