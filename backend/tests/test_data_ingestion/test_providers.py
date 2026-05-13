"""Tests for data provider adapters (unit, no network calls)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from features.data_ingestion.providers import get_provider
from features.data_ingestion.yfinance_provider import (
    _is_daily_max_request,
    _MAX_HISTORY_CUTOFF,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n: int = 5, use_datetime_col: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    prices = 100 + np.arange(n, dtype=float)
    col = "Datetime" if use_datetime_col else "Date"
    return pd.DataFrame({
        col: dates,
        "Open": prices * 0.99,
        "High": prices * 1.01,
        "Low": prices * 0.98,
        "Close": prices,
        "Volume": [1_000_000] * n,
    })


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_get_polygon_provider(self):
        provider = get_provider("polygon")
        assert provider.name == "polygon"

    def test_get_alpaca_provider(self):
        with patch("alpaca.data.historical.StockHistoricalDataClient"):
            provider = get_provider("alpaca")
            assert provider.name == "alpaca"

    def test_get_yfinance_provider(self):
        provider = get_provider("yfinance")
        assert provider.name == "yfinance"

    def test_get_fmp_provider(self):
        provider = get_provider("fmp")
        assert provider.name == "fmp"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown_provider")


# ---------------------------------------------------------------------------
# Base provider timeframe mapping (uses polygon which inherits base)
# ---------------------------------------------------------------------------

class TestBaseProviderTimeframeMapping:
    def test_valid_timeframes(self):
        provider = get_provider("polygon")
        for tf, (mult, span) in [
            ("1m", (1, "minute")),
            ("1h", (1, "hour")),
            ("1d", (1, "day")),
        ]:
            assert provider._timeframe_to_provider_params(tf) == (mult, span)

    def test_invalid_timeframe_raises(self):
        provider = get_provider("polygon")
        with pytest.raises(ValueError):
            provider._timeframe_to_provider_params("3d")


# ---------------------------------------------------------------------------
# yfinance helpers
# ---------------------------------------------------------------------------

class TestIsMaxRequest:
    def test_daily_with_old_start_is_max(self):
        old_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        assert _is_daily_max_request("1d", old_start) is True

    def test_daily_exactly_at_cutoff_is_max(self):
        assert _is_daily_max_request("1d", _MAX_HISTORY_CUTOFF) is True

    def test_daily_recent_start_is_not_max(self):
        recent = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert _is_daily_max_request("1d", recent) is False

    def test_intraday_with_old_start_is_not_max(self):
        old_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        assert _is_daily_max_request("1h", old_start) is False


# ---------------------------------------------------------------------------
# YFinanceProvider fetch_ohlcv
# ---------------------------------------------------------------------------

class TestYFinanceProviderFetchOHLCV:
    @pytest.fixture
    def provider(self):
        return get_provider("yfinance")

    @pytest.fixture
    def start(self):
        return datetime(2020, 1, 1, tzinfo=timezone.utc)

    @pytest.fixture
    def end(self):
        return datetime(2020, 3, 31, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_returns_ohlcv_records(self, provider, start, end):
        df = _make_ohlcv_df(n=5)
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_with_retry",
            new=AsyncMock(return_value=df),
        ):
            records = await provider.fetch_ohlcv("AAPL", "1d", start, end, asset_id=1)
        assert len(records) == 5
        assert all(r.source == "yfinance" for r in records)
        assert all(r.asset_id == 1 for r in records)

    @pytest.mark.asyncio
    async def test_returns_empty_on_none_df(self, provider, start, end):
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_with_retry",
            new=AsyncMock(return_value=None),
        ):
            records = await provider.fetch_ohlcv("AAPL", "1d", start, end, asset_id=1)
        assert records == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_empty_df(self, provider, start, end):
        empty_df = pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_with_retry",
            new=AsyncMock(return_value=empty_df),
        ):
            records = await provider.fetch_ohlcv("AAPL", "1d", start, end, asset_id=1)
        assert records == []

    @pytest.mark.asyncio
    async def test_handles_datetime_column(self, provider, start, end):
        """Should parse both 'Date' and 'Datetime' index column names."""
        df = _make_ohlcv_df(n=3, use_datetime_col=True)
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_with_retry",
            new=AsyncMock(return_value=df),
        ):
            records = await provider.fetch_ohlcv("AAPL", "1h", start, end, asset_id=2)
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_uses_period_max_for_old_daily_start(self, provider, end):
        """When start is at/before 1970-01-01 and timeframe is 1d, must use period='max'."""
        old_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        df = _make_ohlcv_df(n=2)
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_with_retry",
            new=AsyncMock(return_value=df),
        ) as mock_fetch:
            await provider.fetch_ohlcv("MSFT", "1d", old_start, end, asset_id=3)
            _, kwargs = mock_fetch.call_args
            # use_max is the 3rd positional arg
            args = mock_fetch.call_args[0]
            assert args[2] is True  # use_max=True

    @pytest.mark.asyncio
    async def test_does_not_use_period_max_for_intraday(self, provider, end):
        """Intraday requests must never use period='max'."""
        old_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        df = _make_ohlcv_df(n=2)
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_with_retry",
            new=AsyncMock(return_value=df),
        ) as mock_fetch:
            await provider.fetch_ohlcv("MSFT", "1h", old_start, end, asset_id=3)
            args = mock_fetch.call_args[0]
            assert args[2] is False  # use_max=False


# ---------------------------------------------------------------------------
# _fetch_with_retry retry logic
# ---------------------------------------------------------------------------

class TestFetchWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        from features.data_ingestion.yfinance_provider import _fetch_with_retry

        df = _make_ohlcv_df(n=3)
        with patch(
            "features.data_ingestion.yfinance_provider._fetch_history_sync",
            return_value=df,
        ):
            result = await _fetch_with_retry("AAPL", "1d", False, "2020-01-01", "2020-03-31")
        assert result is df

    @pytest.mark.asyncio
    async def test_retries_on_transient_error_then_succeeds(self):
        from features.data_ingestion.yfinance_provider import _fetch_with_retry

        df = _make_ohlcv_df(n=2)
        call_count = 0

        def flaky(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return df

        with patch("features.data_ingestion.yfinance_provider._fetch_history_sync", side_effect=flaky):
            with patch("asyncio.sleep", new=AsyncMock()):
                result = await _fetch_with_retry("AAPL", "1d", False, "2020-01-01", "2020-03-31")
        assert result is df
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        from features.data_ingestion.yfinance_provider import _fetch_with_retry

        with patch(
            "features.data_ingestion.yfinance_provider._fetch_history_sync",
            side_effect=ConnectionError("persistent"),
        ):
            with patch("asyncio.sleep", new=AsyncMock()):
                with pytest.raises(ConnectionError, match="persistent"):
                    await _fetch_with_retry("AAPL", "1d", False, "2020-01-01", "2020-03-31")


# ---------------------------------------------------------------------------
# YFinanceProvider fetch_fundamentals
# ---------------------------------------------------------------------------

class TestYFinanceProviderFetchFundamentals:
    @pytest.mark.asyncio
    async def test_returns_fundamental_records(self):
        provider = get_provider("yfinance")
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "trailingPE": 25.5,
            "marketCap": 3_000_000_000_000,
            "debtToEquity": 1.2,
        }
        with patch(
            "features.data_ingestion.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            records = await provider.fetch_fundamentals("AAPL", asset_id=1)
        assert len(records) == 3
        metric_names = {r.metric_name for r in records}
        assert "trailingPE" in metric_names
        assert "marketCap" in metric_names

    @pytest.mark.asyncio
    async def test_returns_empty_on_missing_info(self):
        provider = get_provider("yfinance")
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        with patch(
            "features.data_ingestion.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            records = await provider.fetch_fundamentals("AAPL", asset_id=1)
        assert records == []

    @pytest.mark.asyncio
    async def test_dividend_yield_fraction_unchanged(self):
        provider = get_provider("yfinance")
        mock_ticker = MagicMock()
        mock_ticker.info = {"dividendYield": 0.04}
        with patch(
            "features.data_ingestion.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            records = await provider.fetch_fundamentals("XOM", asset_id=1)
        dy = next(r for r in records if r.metric_name == "dividendYield")
        assert dy.value == pytest.approx(0.04)

    @pytest.mark.asyncio
    async def test_dividend_yield_percent_points_normalized(self):
        provider = get_provider("yfinance")
        mock_ticker = MagicMock()
        mock_ticker.info = {"dividendYield": 2.16}
        with patch(
            "features.data_ingestion.yfinance_provider.yf.Ticker",
            return_value=mock_ticker,
        ):
            records = await provider.fetch_fundamentals("SBLK", asset_id=1)
        dy = next(r for r in records if r.metric_name == "dividendYield")
        assert dy.value == pytest.approx(0.0216)
