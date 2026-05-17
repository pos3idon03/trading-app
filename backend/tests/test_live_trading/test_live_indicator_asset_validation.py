"""Tests verifying live indicator endpoint asset validation and graceful fallback."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_bars(n: int = 35) -> list:
    """Return a minimal list of mock OHLCV bars sufficient for indicator calculation."""
    bar = MagicMock()
    bar.open = 150.0
    bar.high = 155.0
    bar.low = 148.0
    bar.close = 152.0
    bar.volume = 1_000_000
    return [bar] * n


# ---------------------------------------------------------------------------
# GET /indicators/{symbol}: 404 path (no bars + unregistered asset)
# ---------------------------------------------------------------------------

class TestIndicatorsAssetValidation:
    def test_unknown_asset_no_bars_returns_404(self):
        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_res.return_value.get_bars.return_value = []
            response = client.get("/api/v1/live/indicators/FAKE?timeframe=1h")

        assert response.status_code == 404
        assert "not registered" in response.json()["detail"].lower()

    def test_unknown_asset_with_live_bars_returns_200(self):
        """Graceful fallback: bars are present but asset is not in DB yet."""
        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=None),
            ),
            patch("routes.live_trading.compute_indicators") as mock_compute,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
        ):
            mock_res.return_value.get_bars.return_value = _make_bars()
            snapshot = MagicMock()
            snapshot.symbol = "AAPL"
            snapshot.timeframe = "1h"
            snapshot.close_price = 152.0
            snapshot.rsi = 55.0
            snapshot.macd = 0.5
            snapshot.macd_signal = 0.3
            snapshot.macd_histogram = 0.2
            snapshot.bb_upper = 160.0
            snapshot.bb_middle = 152.0
            snapshot.bb_lower = 144.0
            snapshot.vwap = 151.0
            snapshot.bb_percent = 0.5
            mock_compute.return_value = snapshot
            mock_dal.create_indicator = AsyncMock()

            response = client.get("/api/v1/live/indicators/AAPL?timeframe=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["close_price"] == 152.0
        assert data["asset_id"] is None
        mock_dal.create_indicator.assert_not_awaited()

    def test_known_asset_with_live_bars_persists_and_returns(self):
        """When asset IS registered and bars exist, indicator is persisted to DB."""
        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=7),
            ),
            patch("routes.live_trading.compute_indicators") as mock_compute,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
        ):
            mock_res.return_value.get_bars.return_value = _make_bars()
            snapshot = MagicMock()
            snapshot.symbol = "AAPL"
            snapshot.timeframe = "1h"
            snapshot.close_price = 152.0
            snapshot.rsi = 55.0
            snapshot.macd = 0.5
            snapshot.macd_signal = 0.3
            snapshot.macd_histogram = 0.2
            snapshot.bb_upper = 160.0
            snapshot.bb_middle = 152.0
            snapshot.bb_lower = 144.0
            snapshot.vwap = 151.0
            snapshot.bb_percent = 0.5
            mock_compute.return_value = snapshot
            mock_dal.create_indicator = AsyncMock()

            response = client.get("/api/v1/live/indicators/AAPL?timeframe=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == 7
        mock_dal.create_indicator.assert_awaited_once()

    def test_known_asset_with_no_bars_returns_empty_snapshot(self):
        with (
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=1),
            ),
            patch("routes.live_trading._get_resampler") as mock_res,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
        ):
            mock_res.return_value.get_bars.return_value = []
            mock_dal.get_latest_indicator = AsyncMock(return_value=None)

            response = client.get("/api/v1/live/indicators/AAPL?timeframe=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["asset_id"] == 1
        assert data["close_price"] == 0.0

    def test_symbol_is_uppercased_in_db_path(self):
        looked_up = {}

        async def capture_lookup(session, symbol):
            looked_up["symbol"] = symbol
            return None

        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                side_effect=capture_lookup,
            ),
        ):
            mock_res.return_value.get_bars.return_value = []
            client.get("/api/v1/live/indicators/aapl?timeframe=1h")

        assert looked_up.get("symbol") == "AAPL"

    def test_stored_indicator_includes_asset_id(self):
        mock_stored = MagicMock()
        mock_stored.asset_id = 5
        mock_stored.symbol = "MSFT"
        mock_stored.timeframe = "1h"
        mock_stored.close_price = 420.0
        mock_stored.rsi = 55.0
        mock_stored.macd = None
        mock_stored.macd_signal = None
        mock_stored.macd_histogram = None
        mock_stored.bb_upper = None
        mock_stored.bb_middle = None
        mock_stored.bb_lower = None
        mock_stored.vwap = None
        mock_stored.created_at = None

        with (
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=5),
            ),
            patch("routes.live_trading._get_resampler") as mock_res,
            patch("routes.live_trading.live_trading_dal") as mock_dal,
        ):
            mock_res.return_value.get_bars.return_value = []
            mock_dal.get_latest_indicator = AsyncMock(return_value=mock_stored)

            response = client.get("/api/v1/live/indicators/MSFT?timeframe=1h")

        assert response.status_code == 200
        data = response.json()
        assert data["asset_id"] == 5


# ---------------------------------------------------------------------------
# GET /indicators/{symbol}: DB fallback when resampler has few bars
# ---------------------------------------------------------------------------

class TestIndicatorsDbFallback:
    def test_falls_back_to_db_when_resampler_has_few_bars(self):
        """Short resampler bars must not yield close_price=0 when DB has enough OHLCV."""
        resampler_bars = _make_bars(5)
        db_bars = _make_bars(35)
        db_bars[-1].close = 78394.38

        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch(
                "routes.live_trading._fetch_bars_from_db",
                new_callable=AsyncMock,
                return_value=db_bars,
            ),
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=1),
            ),
            patch("routes.live_trading.live_trading_dal") as mock_dal,
        ):
            mock_res.return_value.get_bars.return_value = resampler_bars
            mock_dal.create_indicator = AsyncMock()

            response = client.get("/api/v1/live/indicators/BTC-USD?timeframe=5m")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC-USD"
        assert data["timeframe"] == "5m"
        assert data["close_price"] == 78394.38

    def test_skips_db_fallback_when_resampler_has_enough_bars(self):
        resampler_bars = _make_bars(35)
        with (
            patch("routes.live_trading._get_resampler") as mock_res,
            patch(
                "routes.live_trading._fetch_bars_from_db",
                new_callable=AsyncMock,
            ) as mock_db,
            patch(
                "routes.live_trading.get_asset_id_by_symbol",
                new=AsyncMock(return_value=1),
            ),
            patch("routes.live_trading.live_trading_dal") as mock_dal,
        ):
            mock_res.return_value.get_bars.return_value = resampler_bars
            mock_dal.create_indicator = AsyncMock()

            response = client.get("/api/v1/live/indicators/AAPL?timeframe=1h")

        assert response.status_code == 200
        assert response.json()["close_price"] == 152.0
        mock_db.assert_not_called()


# ---------------------------------------------------------------------------
# POST /start: auto-registers assets in the DB
# ---------------------------------------------------------------------------

class TestStreamStartAutoRegistration:
    def test_start_stream_calls_register_for_each_symbol(self):
        registered = {}

        async def capture_upsert(session, symbol, **kwargs):
            registered[symbol] = True
            return 1

        with (
            patch("routes.live_trading.get_stream") as mock_stream,
            patch("routes.live_trading.upsert_asset", side_effect=capture_upsert),
        ):
            mock_status = MagicMock()
            mock_status.connected = True
            mock_status.subscribed_symbols = ["AAPL", "MSFT"]
            mock_status.last_tick_at = None
            mock_status.error = None
            mock_status.reconnect_count = 0
            stream_instance = MagicMock()
            stream_instance.status = mock_status
            stream_instance.start = AsyncMock()
            stream_instance.on_tick = MagicMock()
            mock_stream.return_value = stream_instance

            response = client.post(
                "/api/v1/live/start", json={"symbols": ["AAPL", "MSFT"]}
            )

        assert response.status_code == 200
        assert "AAPL" in registered
        assert "MSFT" in registered

    def test_start_stream_continues_when_upsert_fails(self):
        """A DB error during asset registration must not abort the stream start."""
        async def failing_upsert(session, symbol, **kwargs):
            raise RuntimeError("DB unavailable")

        with (
            patch("routes.live_trading.get_stream") as mock_stream,
            patch("routes.live_trading.upsert_asset", side_effect=failing_upsert),
        ):
            mock_status = MagicMock()
            mock_status.connected = True
            mock_status.subscribed_symbols = ["AAPL"]
            mock_status.last_tick_at = None
            mock_status.error = None
            mock_status.reconnect_count = 0
            stream_instance = MagicMock()
            stream_instance.status = mock_status
            stream_instance.start = AsyncMock()
            stream_instance.on_tick = MagicMock()
            mock_stream.return_value = stream_instance

            response = client.post("/api/v1/live/start", json={"symbols": ["AAPL"]})

        assert response.status_code == 200
