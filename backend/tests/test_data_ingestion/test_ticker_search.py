"""Tests for the ticker search feature and endpoint."""
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Feature: search_tickers
# ---------------------------------------------------------------------------

_POLYGON_RESPONSE = {
    "results": [
        {
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "type": "CS",
            "primary_exchange": "XNAS",
        },
        {
            "ticker": "MSTR",
            "name": "MicroStrategy Incorporated",
            "type": "CS",
            "primary_exchange": "XNAS",
        },
    ],
    "status": "OK",
    "count": 2,
}


class TestSearchTickers:
    @pytest.mark.asyncio
    async def test_returns_results_from_polygon(self):
        from features.data_ingestion.ticker_search import search_tickers

        with patch(
            "features.data_ingestion.ticker_search.fetch_json",
            new=AsyncMock(return_value=_POLYGON_RESPONSE),
        ):
            response = await search_tickers(query="Micro", limit=10)

        assert response.count == 2
        assert response.results[0].symbol == "MSFT"
        assert response.results[0].name == "Microsoft Corporation"
        assert response.results[0].asset_type == "stock"
        assert response.results[0].exchange == "XNAS"

    @pytest.mark.asyncio
    async def test_returns_empty_on_polygon_error(self):
        from features.data_ingestion.ticker_search import search_tickers

        with patch(
            "features.data_ingestion.ticker_search.fetch_json",
            new=AsyncMock(side_effect=Exception("Polygon unavailable")),
        ):
            response = await search_tickers(query="AAPL", limit=10)

        assert response.count == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_respects_limit_cap(self):
        from features.data_ingestion.ticker_search import search_tickers

        captured: dict = {}

        async def mock_fetch(url, params=None, **kwargs):
            captured["params"] = params
            return {"results": []}

        with patch("features.data_ingestion.ticker_search.fetch_json", new=mock_fetch):
            await search_tickers(query="Apple", limit=100)

        assert captured["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_handles_empty_polygon_results(self):
        from features.data_ingestion.ticker_search import search_tickers

        with patch(
            "features.data_ingestion.ticker_search.fetch_json",
            new=AsyncMock(return_value={"results": [], "status": "OK"}),
        ):
            response = await search_tickers(query="ZZZZ", limit=10)

        assert response.count == 0
        assert response.results == []

    @pytest.mark.asyncio
    async def test_passes_query_to_polygon(self):
        from features.data_ingestion.ticker_search import search_tickers

        captured: dict = {}

        async def mock_fetch(url, params=None, **kwargs):
            captured["params"] = params
            return {"results": []}

        with patch("features.data_ingestion.ticker_search.fetch_json", new=mock_fetch):
            await search_tickers(query="Tesla", limit=5)

        assert captured["params"]["search"] == "Tesla"
        assert captured["params"]["active"] == "true"


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
                TickerSearchResult(symbol="MSFT", name="Microsoft Corporation", exchange="XNAS")
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
