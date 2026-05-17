from datetime import datetime, timezone
from typing import Optional

from config import get_settings
from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from utils.logging import get_logger

from .base_provider import DataProvider

logger = get_logger(__name__)

ALPACA_TIMEFRAME_MAP = {
    "1m": "1Min",
    "5m": "5Min",
    "15m": "15Min",
    "30m": "30Min",
    "1h": "1Hour",
    "4h": "4Hour",
    "1d": "1Day",
    "1w": "1Week",
}


class AlpacaProvider(DataProvider):
    """Alpaca market data + execution provider."""

    def __init__(self) -> None:
        settings = get_settings()
        from alpaca.data.historical import StockHistoricalDataClient
        self._client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
        )

    @property
    def name(self) -> str:
        return "alpaca"

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        asset_id: Optional[int] = None,
        asset_type: Optional[str] = None,
    ) -> list[OHLCVRecord]:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        alpaca_tf = self._to_alpaca_timeframe(timeframe)
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=alpaca_tf,
            start=start,
            end=end,
            adjustment="all",
        )
        bars = self._client.get_stock_bars(request)
        df = bars.df.reset_index()
        records = []
        for _, row in df.iterrows():
            records.append(OHLCVRecord(
                time=row["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc),
                asset_id=asset_id or 0,
                timeframe=timeframe,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                vwap=float(row["vwap"]) if "vwap" in row else None,
                trade_count=int(row["trade_count"]) if "trade_count" in row else None,
                source=self.name,
            ))
        logger.info("alpaca_ohlcv_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        """Alpaca does not offer fundamentals — return empty."""
        logger.warning("alpaca_no_fundamentals", symbol=symbol)
        return []

    def _to_alpaca_timeframe(self, timeframe: str):
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        mapping = {
            "1m": TimeFrame(1, TimeFrameUnit.Minute),
            "5m": TimeFrame(5, TimeFrameUnit.Minute),
            "15m": TimeFrame(15, TimeFrameUnit.Minute),
            "30m": TimeFrame(30, TimeFrameUnit.Minute),
            "1h": TimeFrame(1, TimeFrameUnit.Hour),
            "4h": TimeFrame(4, TimeFrameUnit.Hour),
            "1d": TimeFrame(1, TimeFrameUnit.Day),
            "1w": TimeFrame(1, TimeFrameUnit.Week),
        }
        if timeframe not in mapping:
            raise ValueError(f"Alpaca does not support timeframe: {timeframe}")
        return mapping[timeframe]
