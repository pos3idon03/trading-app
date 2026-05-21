from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from dtos.market_data_dto import OHLCVBackfillRequest
from features.ingestion.ohlcv_orchestrator import _backfill_one, _effective_sources


def test_effective_sources_adds_crypto_for_crypto_asset():
    assert "tiingo_crypto" in _effective_sources("crypto", ["tiingo_eod", "tiingo_iex"])


def test_effective_sources_unchanged_for_stock():
    sources = ["tiingo_eod", "tiingo_iex"]
    assert _effective_sources("stock", sources) == sources


@pytest.mark.asyncio
async def test_backfill_crypto_uses_crypto_client_not_eod():
    inst = {
        "id": 1,
        "symbol": "BTC-USD",
        "tiingo_ticker": "btcusd",
        "asset_type": "crypto",
    }
    request = OHLCVBackfillRequest(
        symbols=["BTC-USD"],
        timeframes=["1d", "5m"],
        sources=["tiingo_eod", "tiingo_iex"],
    )
    session = AsyncMock()

    with patch(
        "features.ingestion.ohlcv_orchestrator.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=inst),
    ), patch(
        "features.ingestion.ohlcv_orchestrator.check_and_increment",
        new=AsyncMock(),
    ), patch(
        "features.ingestion.ohlcv_orchestrator.ohlcv_dal.get_latest_timestamp",
        new=AsyncMock(return_value=None),
    ), patch(
        "features.ingestion.ohlcv_orchestrator.crypto_client.fetch_crypto_bars",
        new=AsyncMock(return_value=[]),
    ) as mock_crypto, patch(
        "features.ingestion.ohlcv_orchestrator.eod_client.fetch_eod_bars",
        new=AsyncMock(return_value=[]),
    ) as mock_eod, patch(
        "features.ingestion.ohlcv_orchestrator.iex_client.fetch_iex_bars",
        new=AsyncMock(return_value=[]),
    ) as mock_iex, patch(
        "features.ingestion.ohlcv_orchestrator.ohlcv_dal.bulk_insert_ohlcv",
        new=AsyncMock(return_value=0),
    ):
        result = await _backfill_one(session, "BTC-USD", request)

    assert result["status"] == "ok"
    assert mock_crypto.await_count == 2
    mock_eod.assert_not_awaited()
    mock_iex.assert_not_awaited()
    timeframes = {call.args[2] for call in mock_crypto.await_args_list}
    assert timeframes == {"1d", "5m"}


@pytest.mark.asyncio
async def test_backfill_stock_uses_eod_and_iex():
    inst = {
        "id": 2,
        "symbol": "AAPL",
        "tiingo_ticker": "AAPL",
        "asset_type": "stock",
    }
    request = OHLCVBackfillRequest(
        symbols=["AAPL"],
        timeframes=["1d", "5m"],
        sources=["tiingo_eod", "tiingo_iex"],
    )
    session = AsyncMock()

    with patch(
        "features.ingestion.ohlcv_orchestrator.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=inst),
    ), patch(
        "features.ingestion.ohlcv_orchestrator.check_and_increment",
        new=AsyncMock(),
    ), patch(
        "features.ingestion.ohlcv_orchestrator.ohlcv_dal.get_latest_timestamp",
        new=AsyncMock(return_value=None),
    ), patch(
        "features.ingestion.ohlcv_orchestrator.crypto_client.fetch_crypto_bars",
        new=AsyncMock(return_value=[]),
    ) as mock_crypto, patch(
        "features.ingestion.ohlcv_orchestrator.eod_client.fetch_eod_bars",
        new=AsyncMock(return_value=[]),
    ) as mock_eod, patch(
        "features.ingestion.ohlcv_orchestrator.iex_client.fetch_iex_bars",
        new=AsyncMock(return_value=[]),
    ) as mock_iex, patch(
        "features.ingestion.ohlcv_orchestrator.ohlcv_dal.bulk_insert_ohlcv",
        new=AsyncMock(return_value=0),
    ):
        result = await _backfill_one(session, "AAPL", request)

    assert result["status"] == "ok"
    mock_eod.assert_awaited_once()
    mock_iex.assert_awaited_once()
    mock_crypto.assert_not_awaited()
