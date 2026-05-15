"""Tests for assets listing and symbol-based OHLCV endpoints."""
import math
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import numpy as np
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

    @pytest.mark.asyncio
    async def test_default_start_is_epoch(self):
        """When no start param is given, the route must query from 1970-01-01 (not 2020)."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)
        df = _make_ohlcv_df()
        mock_get_ohlcv = AsyncMock(return_value=df)

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=mock_get_ohlcv), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            client.get("/ohlcv/by-symbol/AAPL?timeframe=1d")

        _args, kwargs = mock_get_ohlcv.call_args
        # signature: get_ohlcv(session, asset_id, timeframe, start, end, ...)
        start_used = kwargs.get("start") if "start" in kwargs else _args[3]
        assert start_used == datetime(1970, 1, 1, tzinfo=timezone.utc), (
            f"Expected epoch start 1970-01-01, got {start_used}"
        )

    @pytest.mark.asyncio
    async def test_default_start_is_epoch_asset_id_route(self):
        """When no start param is given on the asset_id route, query starts from 1970-01-01."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)
        df = _make_ohlcv_df()
        mock_get_ohlcv = AsyncMock(return_value=df)

        with patch("routes.data_ingestion.get_ohlcv", new=mock_get_ohlcv), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            client.get("/ohlcv/1?timeframe=1d")

        _args, kwargs = mock_get_ohlcv.call_args
        # signature: get_ohlcv(session, asset_id, timeframe, start, end, ...)
        start_used = kwargs.get("start") if "start" in kwargs else _args[3]
        assert start_used == datetime(1970, 1, 1, tzinfo=timezone.utc), (
            f"Expected epoch start 1970-01-01, got {start_used}"
        )


# ---------------------------------------------------------------------------
# NaN / Inf sanitization
# ---------------------------------------------------------------------------

def _make_ohlcv_df_with_nan(n: int = 3) -> pd.DataFrame:
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    times = [base.replace(day=i + 1) for i in range(n)]
    return pd.DataFrame({
        "time": times,
        "open": [100.0] * n,
        "high": [105.0] * n,
        "low": [95.0] * n,
        "close": [102.0] * n,
        "volume": [1_000_000] * n,
        "vwap": [float("nan")] * n,
        "source": ["yfinance"] * n,
    })


class TestNaNSanitization:
    """Verify NaN values do not reach JSON serialization."""

    def test_nan_to_none_helper_converts_nan(self):
        from routes.data_ingestion import _nan_to_none

        assert _nan_to_none(float("nan")) is None

    def test_nan_to_none_helper_converts_inf(self):
        from routes.data_ingestion import _nan_to_none

        assert _nan_to_none(float("inf")) is None
        assert _nan_to_none(float("-inf")) is None

    def test_nan_to_none_helper_passes_valid_float(self):
        from routes.data_ingestion import _nan_to_none

        assert _nan_to_none(3.14) == 3.14

    def test_nan_to_none_helper_passes_none(self):
        from routes.data_ingestion import _nan_to_none

        assert _nan_to_none(None) is None

    def test_build_ohlcv_records_nan_vwap_becomes_none(self):
        from routes.data_ingestion import _build_ohlcv_records

        df = _make_ohlcv_df_with_nan(n=2)
        records = _build_ohlcv_records(df, asset_id=1, timeframe="1d")

        assert len(records) == 2
        for rec in records:
            assert rec.vwap is None

    @pytest.mark.asyncio
    async def test_endpoint_returns_200_with_nan_vwap(self):
        """Route must return HTTP 200 (no 500) when vwap contains NaN."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from routes.data_ingestion import router

        app = FastAPI()
        app.include_router(router)
        df = _make_ohlcv_df_with_nan(n=3)

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=3)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(return_value=df)), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(app)
            response = client.get("/ohlcv/by-symbol/MSFT?timeframe=1d")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 3
        for record in body["records"]:
            assert record["vwap"] is None

    def test_sanitize_nan_in_dal(self):
        """_sanitize_nan should replace NaN with None in all float columns."""
        from dal.market_data_dal import _sanitize_nan

        df = pd.DataFrame({
            "time": [datetime(2023, 1, 1, tzinfo=timezone.utc)],
            "open": [100.0],
            "vwap": [float("nan")],
        })
        result = _sanitize_nan(df)
        assert result["vwap"].iloc[0] is None

    def test_sanitize_nan_passes_valid_values(self):
        """_sanitize_nan should leave non-NaN values unchanged."""
        from dal.market_data_dal import _sanitize_nan

        df = pd.DataFrame({
            "time": [datetime(2023, 1, 1, tzinfo=timezone.utc)],
            "open": [100.0],
            "vwap": [101.5],
        })
        result = _sanitize_nan(df)
        assert result["vwap"].iloc[0] == 101.5

    def test_ohlcv_record_dto_coerces_nan_vwap_to_none(self):
        """OHLCVRecord should coerce NaN vwap to None (not raise)."""
        from dtos.market_data_dto import OHLCVRecord

        rec = OHLCVRecord(
            time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            asset_id=1,
            timeframe="1d",
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000,
            vwap=float("nan"),
            source="yfinance",
        )
        assert rec.vwap is None

    def test_ohlcv_record_dto_rejects_nan_price(self):
        """OHLCVRecord should raise ValueError when a required price field is NaN."""
        import pydantic

        from dtos.market_data_dto import OHLCVRecord

        with pytest.raises((ValueError, pydantic.ValidationError)):
            OHLCVRecord(
                time=datetime(2023, 1, 1, tzinfo=timezone.utc),
                asset_id=1,
                timeframe="1d",
                open=float("nan"),
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000,
                source="yfinance",
            )


# ---------------------------------------------------------------------------
# DAL: delete_asset
# ---------------------------------------------------------------------------

class TestDeleteAssetDAL:
    @pytest.mark.asyncio
    async def test_returns_true_when_asset_exists(self):
        """delete_asset should return True when the DELETE affects one row."""
        from dal.market_data_dal import delete_asset

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await delete_asset(mock_session, "AAPL")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_asset_not_found(self):
        """delete_asset should return False when no rows are affected."""
        from dal.market_data_dal import delete_asset

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await delete_asset(mock_session, "UNKNOWN")
        assert result is False

    @pytest.mark.asyncio
    async def test_uppercases_symbol(self):
        """delete_asset should normalise the symbol to uppercase."""
        from dal.market_data_dal import delete_asset

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await delete_asset(mock_session, "aapl")
        assert result is True


# ---------------------------------------------------------------------------
# Route: DELETE /assets/{symbol}
# ---------------------------------------------------------------------------

class TestDeleteAssetRoute:
    @pytest.mark.asyncio
    async def test_delete_existing_asset_returns_200(self):
        """DELETE /assets/{symbol} should return 200 and deleted=True for an existing asset."""
        from httpx import AsyncClient, ASGITransport
        from main import app

        with (
            patch("routes.data_ingestion.delete_asset", new_callable=AsyncMock) as mock_del,
            patch("db.get_db"),
        ):
            mock_del.return_value = True
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.delete("/data/assets/AAPL")

        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert body["symbol"] == "AAPL"
        assert "deleted" in body["message"].lower() or "success" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_unknown_asset_returns_404(self):
        """DELETE /assets/{symbol} should return 404 when the asset does not exist."""
        from httpx import AsyncClient, ASGITransport
        from main import app

        with (
            patch("routes.data_ingestion.delete_asset", new_callable=AsyncMock) as mock_del,
            patch("db.get_db"),
        ):
            mock_del.return_value = False
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.delete("/data/assets/UNKNOWN")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_normalises_symbol_to_uppercase(self):
        """DELETE /assets/{symbol} should uppercase the symbol before passing it to the DAL."""
        from httpx import AsyncClient, ASGITransport
        from main import app

        with (
            patch("routes.data_ingestion.delete_asset", new_callable=AsyncMock) as mock_del,
            patch("db.get_db"),
        ):
            mock_del.return_value = True
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.delete("/data/assets/msft")

        assert resp.status_code == 200
        assert resp.json()["symbol"] == "MSFT"


# ---------------------------------------------------------------------------
# DAL: list_assets_with_latest_price
# ---------------------------------------------------------------------------

def _make_assets_with_price_rows() -> list[dict]:
    return [
        {
            "id": 1, "symbol": "AAPL", "name": "Apple Inc.", "asset_type": "stock",
            "exchange": "NASDAQ", "currency": "USD", "is_active": True,
            "latest_close": 175.50,
            "latest_update": datetime(2024, 1, 15, tzinfo=timezone.utc),
        },
        {
            "id": 2, "symbol": "MSFT", "name": "Microsoft Corporation", "asset_type": "stock",
            "exchange": "NASDAQ", "currency": "USD", "is_active": True,
            "latest_close": None,
            "latest_update": None,
        },
    ]


class TestListAssetsWithLatestPrice:
    @pytest.mark.asyncio
    async def test_returns_assets_with_price(self):
        from dal.market_data_dal import list_assets_with_latest_price

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": 1, "symbol": "AAPL", "name": "Apple Inc.", "asset_type": "stock",
                "exchange": "NASDAQ", "currency": "USD", "is_active": True,
                "latest_close": 175.50,
                "latest_update": datetime(2024, 1, 15, tzinfo=timezone.utc),
            }
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await list_assets_with_latest_price(mock_session)

        assert len(rows) == 1
        assert rows[0]["symbol"] == "AAPL"
        assert rows[0]["latest_close"] == 175.50

    @pytest.mark.asyncio
    async def test_returns_none_price_for_asset_without_ohlcv(self):
        from dal.market_data_dal import list_assets_with_latest_price

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id": 2, "symbol": "NEW", "name": "New Corp", "asset_type": "stock",
                "exchange": "NYSE", "currency": "USD", "is_active": True,
                "latest_close": None,
                "latest_update": None,
            }
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await list_assets_with_latest_price(mock_session)

        assert rows[0]["latest_close"] is None
        assert rows[0]["latest_update"] is None

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_assets(self):
        from dal.market_data_dal import list_assets_with_latest_price

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        rows = await list_assets_with_latest_price(mock_session)

        assert rows == []


# ---------------------------------------------------------------------------
# Route: GET /assets/with-prices
# ---------------------------------------------------------------------------

class TestGetAssetsWithPricesRoute:
    @pytest.mark.asyncio
    async def test_returns_assets_with_price_fields(self):
        from httpx import AsyncClient, ASGITransport
        from main import app

        rows = _make_assets_with_price_rows()

        with (
            patch("routes.data_ingestion.list_assets_with_latest_price", new=AsyncMock(return_value=rows)),
            patch("db.get_db"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/data/assets/with-prices")

        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        assert body["assets"][0]["symbol"] == "AAPL"
        assert body["assets"][0]["latest_close"] == 175.50
        assert body["assets"][0]["latest_update"] is not None

    @pytest.mark.asyncio
    async def test_returns_null_price_for_asset_without_ohlcv(self):
        from httpx import AsyncClient, ASGITransport
        from main import app

        rows = _make_assets_with_price_rows()

        with (
            patch("routes.data_ingestion.list_assets_with_latest_price", new=AsyncMock(return_value=rows)),
            patch("db.get_db"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/data/assets/with-prices")

        body = resp.json()
        msft = next(a for a in body["assets"] if a["symbol"] == "MSFT")
        assert msft["latest_close"] is None
        assert msft["latest_update"] is None

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_assets(self):
        from httpx import AsyncClient, ASGITransport
        from main import app

        with (
            patch("routes.data_ingestion.list_assets_with_latest_price", new=AsyncMock(return_value=[])),
            patch("db.get_db"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/data/assets/with-prices")

        body = resp.json()
        assert body["count"] == 0
        assert body["assets"] == []


# ---------------------------------------------------------------------------
# Route: GET /ohlcv/by-symbol — resampling fallback
# ---------------------------------------------------------------------------

def _make_intraday_ohlcv_df(n: int = 4) -> pd.DataFrame:
    """n × 5-minute bars starting at 2026-04-14 13:30 UTC."""
    from datetime import timedelta
    base = datetime(2026, 4, 14, 13, 30, tzinfo=timezone.utc)
    times = [base + timedelta(minutes=5 * i) for i in range(n)]
    return pd.DataFrame({
        "time": times,
        "open": [290.0] * n,
        "high": [292.0] * n,
        "low": [289.0] * n,
        "close": [291.0] * n,
        "volume": [50_000] * n,
        "vwap": [290.5] * n,
        "source": ["tiingo"] * n,
    })


def _make_test_app():
    from fastapi import FastAPI
    from routes.data_ingestion import router
    app = FastAPI()
    app.include_router(router)
    return app


class TestOHLCVResamplingFallback:
    """When native timeframe rows are absent, the route must resample from 5m."""

    def test_resamples_1h_from_5m_when_native_empty(self):
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()
        resampled_df = _make_intraday_ohlcv_df(n=12)
        call_count = 0

        def _mock_get_ohlcv(session, asset_id, timeframe, start, end, bucket_interval=None):
            nonlocal call_count
            call_count += 1
            if bucket_interval is None:
                return empty_df
            return resampled_df

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock_get_ohlcv)), \
             patch("routes.data_ingestion.get_db"):
            client = TestClient(_make_test_app())
            resp = client.get("/ohlcv/by-symbol/ADBE?timeframe=1h")

        assert resp.status_code == 200
        body = resp.json()
        assert body["timeframe"] == "1h"
        assert body["count"] == 12
        assert call_count == 2

    def test_resamples_30m_from_5m_when_native_empty(self):
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()
        resampled_df = _make_intraday_ohlcv_df(n=6)

        def _mock(session, asset_id, timeframe, start, end, bucket_interval=None):
            return empty_df if bucket_interval is None else resampled_df

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock)), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/by-symbol/ADBE?timeframe=30m")

        assert resp.status_code == 200
        assert resp.json()["timeframe"] == "30m"

    def test_resamples_15m_from_5m_when_native_empty(self):
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()
        resampled_df = _make_intraday_ohlcv_df(n=3)

        def _mock(session, asset_id, timeframe, start, end, bucket_interval=None):
            return empty_df if bucket_interval is None else resampled_df

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock)), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/by-symbol/ADBE?timeframe=15m")

        assert resp.status_code == 200
        assert resp.json()["timeframe"] == "15m"

    def test_resamples_4h_from_5m_when_native_empty(self):
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()
        resampled_df = _make_intraday_ohlcv_df(n=48)

        def _mock(session, asset_id, timeframe, start, end, bucket_interval=None):
            return empty_df if bucket_interval is None else resampled_df

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock)), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/by-symbol/ADBE?timeframe=4h")

        assert resp.status_code == 200
        assert resp.json()["timeframe"] == "4h"

    def test_returns_404_when_5m_also_empty(self):
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(return_value=empty_df)), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/by-symbol/ADBE?timeframe=1h")

        assert resp.status_code == 404
        assert "No OHLCV data found" in resp.json()["detail"]

    def test_no_resample_attempted_when_native_data_exists(self):
        """If native rows exist, the resample path must not be invoked."""
        from fastapi.testclient import TestClient
        native_df = _make_intraday_ohlcv_df(n=5)
        call_count = 0

        def _mock(session, asset_id, timeframe, start, end, bucket_interval=None):
            nonlocal call_count
            call_count += 1
            return native_df

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock)), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/by-symbol/ADBE?timeframe=5m")

        assert resp.status_code == 200
        assert call_count == 1

    def test_explicit_bucket_param_skips_resample(self):
        """When caller passes ?bucket=..., the resample fallback must not activate."""
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()
        call_count = 0

        def _mock(session, asset_id, timeframe, start, end, bucket_interval=None):
            nonlocal call_count
            call_count += 1
            return empty_df

        with patch("routes.data_ingestion.get_asset_id_by_symbol", new=AsyncMock(return_value=1)), \
             patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock)), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/by-symbol/ADBE?timeframe=1h&bucket=1+hour")

        assert resp.status_code == 404
        assert call_count == 1

    def test_resample_by_asset_id_route(self):
        """The /ohlcv/{asset_id} route must also resample when native TF is empty."""
        from fastapi.testclient import TestClient
        empty_df = pd.DataFrame()
        resampled_df = _make_intraday_ohlcv_df(n=6)

        def _mock(session, asset_id, timeframe, start, end, bucket_interval=None):
            return empty_df if bucket_interval is None else resampled_df

        with patch("routes.data_ingestion.get_ohlcv", new=AsyncMock(side_effect=_mock)), \
             patch("routes.data_ingestion._resolve_symbol", new=AsyncMock(return_value="ADBE")), \
             patch("routes.data_ingestion.get_db"):
            resp = TestClient(_make_test_app()).get("/ohlcv/5?timeframe=1h")

        assert resp.status_code == 200
        assert resp.json()["timeframe"] == "1h"
