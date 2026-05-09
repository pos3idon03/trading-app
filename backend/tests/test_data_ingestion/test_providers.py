"""Tests for data provider adapters (unit, no network calls)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from features.data_ingestion.providers import get_provider


class TestProviderRegistry:
    def test_get_polygon_provider(self):
        provider = get_provider("polygon")
        assert provider.name == "polygon"

    def test_get_alpaca_provider(self):
        with patch("features.data_ingestion.alpaca_provider.StockHistoricalDataClient"):
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


class TestYFinanceProvider:
    @pytest.mark.asyncio
    async def test_fetch_ohlcv_returns_records(self):
        import pandas as pd
        import numpy as np
        from datetime import datetime, timezone, timedelta

        provider = get_provider("yfinance")
        start = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end = datetime(2023, 3, 31, tzinfo=timezone.utc)

        n = 60
        dates = pd.date_range(start, periods=n, freq="D", tz="UTC")
        prices = 100 + np.cumsum(np.random.normal(0, 1, n))
        mock_df = pd.DataFrame({
            "Date": dates,
            "Open": prices * 0.99,
            "High": prices * 1.01,
            "Low": prices * 0.98,
            "Close": prices,
            "Volume": [1_000_000] * n,
        })

        with patch.object(provider, "fetch_ohlcv", new=AsyncMock(return_value=[])):
            records = await provider.fetch_ohlcv("AAPL", "1d", start, end, asset_id=1)
            assert isinstance(records, list)
