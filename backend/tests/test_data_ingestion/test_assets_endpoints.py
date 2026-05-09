"""Tests for assets listing and symbol-based OHLCV endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n: int = 5) -> pd.DataFrame:
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    times = [base.replace(day=i + 1) for i in range(n)]
    return pd.DataFrame({
        "time": times,
        "open": [100.0] * n,
        "high": [105.0] * n,
        "low": [95.0] * n,
        "close": [102.0] * n,
        "volume": [1_000_000] * n,
        "vwap": [101.5] * n,
        "source": ["polygon"] * n,
    })


def _make_asset_rows() -> list[dict]:
    return [
        {"id": 1, "symbol": "AAPL", "name": "Apple Inc.", "asset_type": "stock",
         "exchange": "NASDAQ", "currency": "USD", "is_active": True},
        {"id": 2, "symbol": "MSFT", "name": "Microsoft Corporation", "asset_type": "stock",
         "exchange": "NASDAQ", "currency": "USD", "is_active": True},
    ]


# ---------------------------------------------------------------------------
# DAL: list_assets
# ---------------------------------------------------------------------------

class TestListAssets:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        from dal.market_data_dal import list_assets

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_asset_a = MagicMock(
            id=1, symbol="AAPL", name="Apple Inc.", asset_type="stock",
            exchange="NASDAQ", currency="USD", is_active=True,
        )
        mock_asset_b = MagicMock(
            id=2, symbol="MSFT", name="Microsoft Corporation", asset_type="stock",
            exchange="NASDAQ", currency="USD", is_active=True,
        )
        mock_result.scalars.return_value.all.return_value = [mock_asset_a, mock_asset_b]
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await list_assets(mock_session)

        assert len(rows) == 2
        assert rows[0]["symbol"] == "AAPL"
        assert rows[1]["symbol"] == "MSFT"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_assets(self):
        from dal.market_data_dal import list_assets

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await list_assets(mock_session)

        assert rows == []

    @pytest.mark.asyncio
    async def test_row_keys(self):
        from dal.market_data_dal import list_assets

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_asset = MagicMock(
            id=3, symbol="SPY", name="SPDR S&P 500", asset_type="etf",
            exchange="NYSE", currency="USD", is_active=True,
        )
        mock_result.scalars.return_value.all.return_value = [mock_asset]
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await list_assets(mock_session)

        expected_keys = {"id", "symbol", "name", "asset_type", "exchange", "currency", "is_active"}
        assert set(rows[0].keys()) == expected_keys


# ---------------------------------------------------------------------------
# DAL: get_asset_id_by_symbol normalises to uppercase
# ---------------------------------------------------------------------------

class TestGetAssetIdBySymbol:
    @pytest.mark.asyncio
    async def test_uppercases_symbol(self):
        from dal.market_data_dal import get_asset_id_by_symbol

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (42,)
        mock_session.execute = AsyncMock(return_value=mock_result)

        asset_id = await get_asset_id_by_symbol(mock_session, "msft")

        assert asset_id == 42
        call_args = mock_session.execute.call_args
        # Ensure the WHERE clause used the uppercased symbol
        compiled = str(call_args[0][0])
        assert "symbol" in compiled.lower()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        from dal.market_data_dal import get_asset_id_by_symbol

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_asset_id_by_symbol(mock_session, "UNKNOWN")

        assert result is None


# ---------------------------------------------------------------------------
# Route: GET /assets
# ---------------------------------------------------------------------------

class TestGetAssetsRoute:
    @pytest.mark.asyncio
    async def test_returns_asset_list(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)

        asset_rows = _make_asset_rows()

        with patch("routes.data_ingestion.list_assets", new=AsyncMock(return_value=asset_rows)), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/assets")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert body["assets"][0]["symbol"] == "AAPL"
        assert body["assets"][1]["symbol"] == "MSFT"

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)

        with patch("routes.data_ingestion.list_assets", new=AsyncMock(return_value=[])), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/assets")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 0
        assert body["assets"] == []


# ---------------------------------------------------------------------------
# Route: GET /ohlcv/by-symbol/{symbol}
# ---------------------------------------------------------------------------

class TestGetOHLCVBySymbolRoute:
    @pytest.mark.asyncio
    async def test_returns_records_for_valid_symbol(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)
        df = _make_ohlcv_df()

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=3)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(return_value=df)), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/ohlcv/by-symbol/MSFT?timeframe=1d")

        assert response.status_code == 200
        body = response.json()
        assert body["symbol"] == "MSFT"
        assert body["asset_id"] == 3
        assert body["count"] == 5
        assert len(body["records"]) == 5

    @pytest.mark.asyncio
    async def test_lowercased_symbol_is_normalised(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)
        df = _make_ohlcv_df()

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(return_value=df)), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/ohlcv/by-symbol/aapl")

        assert response.status_code == 200
        assert response.json()["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_unknown_symbol_returns_404(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=None)), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/ohlcv/by-symbol/FAKE")

        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_no_ohlcv_data_returns_404(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=5)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(return_value=pd.DataFrame())), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/ohlcv/by-symbol/EMPTY?timeframe=1d")

        assert response.status_code == 404
        assert "No OHLCV data found" in response.json()["detail"]
