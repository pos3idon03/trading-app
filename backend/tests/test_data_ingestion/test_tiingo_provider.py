"""Unit tests for TiingoProvider (no real network calls)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from features.data_ingestion.tiingo_provider import (
    TiingoProvider,
    _build_crypto_params,
    _build_iex_params,
    _crypto_response_to_rows,
    _parse_timestamp,
    _row_to_record,
    _RESAMPLE_MAP,
    _SUPPORTED_TIMEFRAMES,
    symbol_to_tiingo_crypto_ticker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _make_row(date: str = "2026-05-11T13:30:00.000Z") -> dict:
    return {
        "date": date,
        "open": 292.0,
        "high": 293.0,
        "low": 291.0,
        "close": 292.5,
        "volume": 50000,
    }


def _make_crypto_payload(tiingo_ticker: str = "btcusd") -> list:
    return [
        {
            "ticker": tiingo_ticker,
            "baseCurrency": "btc",
            "quoteCurrency": "usd",
            "priceData": [
                _make_row(),
                _make_row("2026-05-11T13:35:00.000Z"),
            ],
        }
    ]


def _make_provider() -> TiingoProvider:
    return TiingoProvider()


# ---------------------------------------------------------------------------
# symbol_to_tiingo_crypto_ticker
# ---------------------------------------------------------------------------

class TestSymbolToTiingoCryptoTicker:
    def test_maps_base_quote(self):
        assert symbol_to_tiingo_crypto_ticker("BTC-USD") == "btcusd"

    def test_lowercases(self):
        assert symbol_to_tiingo_crypto_ticker("eth-usd") == "ethusd"

    def test_invalid_symbol_raises(self):
        with pytest.raises(ValueError, match="BASE-QUOTE"):
            symbol_to_tiingo_crypto_ticker("BTCUSD")


# ---------------------------------------------------------------------------
# _parse_timestamp
# ---------------------------------------------------------------------------

class TestParseTimestamp:
    def test_utc_z_suffix(self):
        ts = _parse_timestamp("2026-05-11T13:30:00.000Z")
        assert ts.tzinfo is not None
        assert ts.year == 2026
        assert ts.hour == 13
        assert ts.minute == 30

    def test_offset_suffix(self):
        ts = _parse_timestamp("2026-05-11T13:30:00+00:00")
        assert ts.tzinfo is not None

    def test_naive_gets_utc(self):
        ts = _parse_timestamp("2026-05-11T13:30:00")
        assert ts.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# _build_iex_params / _build_crypto_params
# ---------------------------------------------------------------------------

class TestBuildIexParams:
    def test_contains_required_keys(self):
        params = _build_iex_params(
            "5m",
            _utc(2026, 5, 1), _utc(2026, 5, 14),
            "test-token",
        )
        assert params["startDate"] == "2026-05-01"
        assert params["endDate"] == "2026-05-14"
        assert params["resampleFreq"] == "5min"
        assert params["columns"] == "open,high,low,close,volume"
        assert params["token"] == "test-token"

    def test_resample_map_coverage(self):
        for tf in _SUPPORTED_TIMEFRAMES:
            params = _build_iex_params(tf, _utc(2026, 1, 1), _utc(2026, 1, 31), "tok")
            assert params["resampleFreq"] == _RESAMPLE_MAP[tf]


class TestBuildCryptoParams:
    def test_contains_tickers_and_resample(self):
        params = _build_crypto_params(
            "btcusd", "5m",
            _utc(2026, 5, 1), _utc(2026, 5, 14),
            "test-token",
        )
        assert params["tickers"] == "btcusd"
        assert params["resampleFreq"] == "5min"
        assert params["startDate"] == "2026-05-01"
        assert params["endDate"] == "2026-05-14"
        assert params["token"] == "test-token"
        assert "columns" not in params


# ---------------------------------------------------------------------------
# _crypto_response_to_rows
# ---------------------------------------------------------------------------

class TestCryptoResponseToRows:
    def test_extracts_price_data(self):
        rows = _crypto_response_to_rows(_make_crypto_payload(), "btcusd")
        assert len(rows) == 2

    def test_unknown_ticker_returns_empty(self):
        rows = _crypto_response_to_rows(_make_crypto_payload(), "ethusd")
        assert rows == []


# ---------------------------------------------------------------------------
# _row_to_record
# ---------------------------------------------------------------------------

class TestRowToRecord:
    def test_maps_fields_correctly(self):
        row = _make_row()
        record = _row_to_record(row, asset_id=42, timeframe="5m")
        assert record.open == 292.0
        assert record.high == 293.0
        assert record.low == 291.0
        assert record.close == 292.5
        assert record.volume == 50000
        assert record.asset_id == 42
        assert record.timeframe == "5m"
        assert record.source == "tiingo"
        assert record.time.tzinfo is not None

    def test_null_volume_defaults_to_zero(self):
        row = {**_make_row(), "volume": None}
        record = _row_to_record(row, asset_id=1, timeframe="5m")
        assert record.volume == 0

    def test_missing_volume_defaults_to_zero(self):
        row = {k: v for k, v in _make_row().items() if k != "volume"}
        record = _row_to_record(row, asset_id=1, timeframe="5m")
        assert record.volume == 0


# ---------------------------------------------------------------------------
# TiingoProvider.fetch_ohlcv (IEX / stocks)
# ---------------------------------------------------------------------------

class TestTiingoProviderFetchOHLCV:
    @pytest.fixture
    def provider(self):
        return _make_provider()

    @pytest.fixture
    def start(self):
        return _utc(2026, 5, 1)

    @pytest.fixture
    def end(self):
        return _utc(2026, 5, 14)

    @pytest.mark.asyncio
    async def test_returns_ohlcv_records(self, provider, start, end):
        rows = [_make_row(), _make_row("2026-05-11T13:35:00.000Z")]
        with (
            patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_iex_bars",
                new=AsyncMock(return_value=rows),
            ),
        ):
            mock_settings.return_value.tiingo_api_key = "test-token"
            records = await provider.fetch_ohlcv("AAPL", "5m", start, end, asset_id=1)

        assert len(records) == 2
        assert all(r.source == "tiingo" for r in records)
        assert all(r.timeframe == "5m" for r in records)
        assert all(r.asset_id == 1 for r in records)

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self, provider, start, end):
        with (
            patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_iex_bars",
                new=AsyncMock(return_value=[]),
            ),
        ):
            mock_settings.return_value.tiingo_api_key = "test-token"
            records = await provider.fetch_ohlcv("AAPL", "5m", start, end, asset_id=1)

        assert records == []

    @pytest.mark.asyncio
    async def test_unsupported_timeframe_raises(self, provider, start, end):
        with pytest.raises(ValueError, match="does not support timeframe"):
            await provider.fetch_ohlcv("AAPL", "1d", start, end, asset_id=1)

    @pytest.mark.asyncio
    async def test_unsupported_weekly_timeframe_raises(self, provider, start, end):
        with pytest.raises(ValueError, match="does not support timeframe"):
            await provider.fetch_ohlcv("AAPL", "1w", start, end, asset_id=1)

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self, provider, start, end):
        with patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings:
            mock_settings.return_value.tiingo_api_key = ""
            with pytest.raises(RuntimeError, match="TIINGO_API_KEY"):
                await provider.fetch_ohlcv("AAPL", "5m", start, end, asset_id=1)

    @pytest.mark.asyncio
    async def test_http_error_propagates(self, provider, start, end):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

        with (
            patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_iex_bars",
                new=AsyncMock(side_effect=http_error),
            ),
        ):
            mock_settings.return_value.tiingo_api_key = "test-token"
            with pytest.raises(httpx.HTTPStatusError):
                await provider.fetch_ohlcv("AAPL", "5m", start, end, asset_id=1)

    @pytest.mark.asyncio
    async def test_asset_id_defaults_to_zero(self, provider, start, end):
        rows = [_make_row()]
        with (
            patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_iex_bars",
                new=AsyncMock(return_value=rows),
            ),
        ):
            mock_settings.return_value.tiingo_api_key = "test-token"
            records = await provider.fetch_ohlcv("AAPL", "5m", start, end)

        assert records[0].asset_id == 0

    @pytest.mark.asyncio
    async def test_all_supported_timeframes_accepted(self, provider, start, end):
        rows = [_make_row()]
        for tf in _SUPPORTED_TIMEFRAMES:
            with (
                patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
                patch(
                    "features.data_ingestion.tiingo_provider._fetch_tiingo_iex_bars",
                    new=AsyncMock(return_value=rows),
                ),
            ):
                mock_settings.return_value.tiingo_api_key = "tok"
                records = await provider.fetch_ohlcv("AAPL", tf, start, end, asset_id=1)
            assert len(records) == 1


# ---------------------------------------------------------------------------
# TiingoProvider.fetch_ohlcv (crypto)
# ---------------------------------------------------------------------------

class TestTiingoProviderFetchOHLCVCrypto:
    @pytest.fixture
    def provider(self):
        return _make_provider()

    @pytest.fixture
    def start(self):
        return _utc(2026, 5, 1)

    @pytest.fixture
    def end(self):
        return _utc(2026, 5, 14)

    @pytest.mark.asyncio
    async def test_crypto_uses_crypto_endpoint(self, provider, start, end):
        rows = [_make_row(), _make_row("2026-05-11T13:35:00.000Z")]
        mock_crypto = AsyncMock(return_value=rows)
        mock_iex = AsyncMock()

        with (
            patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_crypto_bars",
                mock_crypto,
            ),
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_iex_bars",
                mock_iex,
            ),
        ):
            mock_settings.return_value.tiingo_api_key = "test-token"
            records = await provider.fetch_ohlcv(
                "BTC-USD", "5m", start, end, asset_id=7, asset_type="crypto"
            )

        assert len(records) == 2
        assert all(r.asset_id == 7 for r in records)
        mock_crypto.assert_called_once()
        mock_iex.assert_not_called()
        call_params = mock_crypto.call_args[0][0]
        assert call_params["tickers"] == "btcusd"
        assert call_params["resampleFreq"] == "5min"

    @pytest.mark.asyncio
    async def test_crypto_empty_price_data(self, provider, start, end):
        with (
            patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings,
            patch(
                "features.data_ingestion.tiingo_provider._fetch_tiingo_crypto_bars",
                new=AsyncMock(return_value=[]),
            ),
        ):
            mock_settings.return_value.tiingo_api_key = "test-token"
            records = await provider.fetch_ohlcv(
                "ETH-USD", "5m", start, end, asset_id=1, asset_type="crypto"
            )

        assert records == []

    @pytest.mark.asyncio
    async def test_invalid_crypto_symbol_raises(self, provider, start, end):
        with patch("features.data_ingestion.tiingo_provider.get_settings") as mock_settings:
            mock_settings.return_value.tiingo_api_key = "test-token"
            with pytest.raises(ValueError, match="BASE-QUOTE"):
                await provider.fetch_ohlcv(
                    "BTCUSD", "5m", start, end, asset_type="crypto"
                )


# ---------------------------------------------------------------------------
# TiingoProvider.fetch_fundamentals
# ---------------------------------------------------------------------------

class TestTiingoProviderFetchFundamentals:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        provider = _make_provider()
        result = await provider.fetch_fundamentals("AAPL", asset_id=1)
        assert result == []


# ---------------------------------------------------------------------------
# Provider registry includes tiingo
# ---------------------------------------------------------------------------

class TestTiingoInRegistry:
    def test_get_tiingo_provider(self):
        from features.data_ingestion.providers import get_provider
        provider = get_provider("tiingo")
        assert provider.name == "tiingo"
        assert isinstance(provider, TiingoProvider)
