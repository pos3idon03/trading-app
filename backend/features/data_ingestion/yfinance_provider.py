from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from utils.logging import get_logger

from .base_provider import DataProvider

logger = get_logger(__name__)

YFINANCE_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "1h",   # yfinance has no native 4h; caller should resample
    "1d": "1d",
    "1w": "1wk",
}

FUNDAMENTAL_METRICS = [
    "trailingPE", "forwardPE", "trailingEps", "forwardEps",
    "debtToEquity", "returnOnEquity", "returnOnAssets",
    "revenueGrowth", "earningsGrowth", "grossMargins",
    "operatingMargins", "profitMargins", "currentRatio",
    "quickRatio", "totalDebt", "freeCashflow", "marketCap",
]


class YFinanceProvider(DataProvider):
    """yfinance wrapper — used for early testing and gap-filling."""

    @property
    def name(self) -> str:
        return "yfinance"

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        asset_id: Optional[int] = None,
    ) -> list[OHLCVRecord]:
        interval = YFINANCE_INTERVAL_MAP.get(timeframe, "1d")
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval=interval,
            auto_adjust=True,
        )
        df = df.reset_index()
        records = []
        for _, row in df.iterrows():
            ts = row.get("Datetime") or row.get("Date")
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            records.append(OHLCVRecord(
                time=ts,
                asset_id=asset_id or 0,
                timeframe=timeframe,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row.get("Volume", 0)),
                source=self.name,
            ))
        logger.info("yfinance_ohlcv_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        now = datetime.now(timezone.utc)
        records = []
        for metric in FUNDAMENTAL_METRICS:
            value = info.get(metric)
            if value is not None:
                records.append(FundamentalRecord(
                    time=now,
                    asset_id=asset_id,
                    metric_name=metric,
                    value=float(value),
                    source=self.name,
                ))
        logger.info("yfinance_fundamentals_fetched", symbol=symbol, count=len(records))
        return records
