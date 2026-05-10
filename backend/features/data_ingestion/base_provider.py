from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from dtos.market_data_dto import FundamentalRecord, OHLCVRecord


class DataProvider(ABC):
    """Abstract base for all market data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        asset_id: Optional[int] = None,
    ) -> list[OHLCVRecord]:
        ...

    @abstractmethod
    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        ...

    async def fetch_financial_statements(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        """Fetch income statement, balance sheet, and cash flow records.

        Providers that support this should override it. Default returns empty list.
        """
        return []

    async def fetch_company_profile(self, symbol: str) -> dict:
        """Fetch qualitative company profile (sector, industry, summary, etc.).

        Providers that support this should override it. Default returns empty dict.
        """
        return {}

    def _timeframe_to_provider_params(self, timeframe: str) -> tuple[int, str]:
        """Convert generic timeframe to (multiplier, timespan) for REST-based providers."""
        mapping = {
            "1m": (1, "minute"),
            "5m": (5, "minute"),
            "15m": (15, "minute"),
            "30m": (30, "minute"),
            "1h": (1, "hour"),
            "4h": (4, "hour"),
            "1d": (1, "day"),
            "1w": (1, "week"),
        }
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return mapping[timeframe]
