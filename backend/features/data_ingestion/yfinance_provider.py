import asyncio
import math
from datetime import datetime, timezone
from functools import partial
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
    "priceToBook", "dividendYield",
    "debtToEquity", "returnOnEquity", "returnOnAssets",
    "revenueGrowth", "earningsGrowth", "grossMargins",
    "operatingMargins", "profitMargins", "currentRatio",
    "quickRatio", "totalDebt", "freeCashflow", "marketCap",
]

_STATEMENT_KEYS = {
    "income_stmt": lambda t: t.income_stmt,
    "balance_sheet": lambda t: t.balance_sheet,
    "cashflow": lambda t: t.cashflow,
}

# Earliest date yfinance will meaningfully serve; request before this just
# means Yahoo clips to the actual IPO date automatically.
_MAX_HISTORY_CUTOFF = datetime(1970, 1, 1, tzinfo=timezone.utc)

_MAX_RETRIES = 3


def _is_daily_max_request(timeframe: str, start: datetime) -> bool:
    """Return True when we want the full available daily history."""
    return timeframe == "1d" and start <= _MAX_HISTORY_CUTOFF


def _fetch_history_sync(symbol: str, interval: str, use_max: bool, start_str: str, end_str: str):
    """Blocking yfinance call — intended to be run in a thread executor."""
    ticker = yf.Ticker(symbol)
    if use_max:
        return ticker.history(period="max", interval=interval, auto_adjust=True)
    return ticker.history(
        start=start_str,
        end=end_str,
        interval=interval,
        auto_adjust=True,
    )


async def _fetch_with_retry(symbol: str, interval: str, use_max: bool, start_str: str, end_str: str):
    """Run blocking fetch in a thread executor with simple exponential back-off retry."""
    loop = asyncio.get_event_loop()
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            fn = partial(_fetch_history_sync, symbol, interval, use_max, start_str, end_str)
            return await loop.run_in_executor(None, fn)
        except Exception as exc:
            if attempt == _MAX_RETRIES:
                raise
            wait = 2 ** attempt
            logger.warning(
                "yfinance_retry",
                symbol=symbol,
                attempt=attempt,
                wait_s=wait,
                error=str(exc),
            )
            await asyncio.sleep(wait)


def _is_missing(value) -> bool:
    """Return True for None or NaN values."""
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return True


def _normalize_dividend_yield_from_yahoo(raw: float) -> float:
    """Store dividend yield as a fraction (0.04 == 4%) for API/UI consistency.

    Yahoo `dividendYield` is usually a fraction, but some payloads use percentage
    points (e.g. 2.16 for 2.16%). Treat values >= 1 as percentage points.
    """
    if raw >= 1.0:
        return raw / 100.0
    return raw


def _fetch_statements_sync(symbol: str) -> dict:
    """Blocking call: fetch all financial statement DataFrames for a symbol."""
    ticker = yf.Ticker(symbol)
    return {key: getter(ticker) for key, getter in _STATEMENT_KEYS.items()}


def _fetch_profile_sync(symbol: str) -> dict:
    """Blocking call: fetch company profile info dict for a symbol."""
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    return {
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "business_summary": info.get("longBusinessSummary"),
        "website": info.get("website"),
        "country": info.get("country"),
        "employees": info.get("fullTimeEmployees"),
        "officers": info.get("companyOfficers", []),
    }


def _df_to_fundamental_records(
    df,
    stmt_type: str,
    asset_id: Optional[int],
    source: str,
) -> list[FundamentalRecord]:
    """Convert a yfinance statement DataFrame to FundamentalRecord list."""
    if df is None or df.empty:
        return []
    records = []
    for col in df.columns:
        ts = col.to_pydatetime() if hasattr(col, "to_pydatetime") else datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        period = ts.strftime("%Y-%m-%d")
        for raw_name, value in df[col].items():
            if _is_missing(value):
                continue
            key = str(raw_name).strip().replace(" ", "_").lower()
            records.append(FundamentalRecord(
                time=ts,
                asset_id=asset_id,
                metric_name=f"{stmt_type}.{key}",
                value=float(value),
                period=period,
                source=source,
            ))
    return records


def _row_to_record(row, ts_col: str, symbol: str, timeframe: str, asset_id: int) -> OHLCVRecord:
    ts = row.get(ts_col) or row.get("Date") or row.get("Datetime")
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return OHLCVRecord(
        time=ts,
        asset_id=asset_id or 0,
        timeframe=timeframe,
        open=float(row["Open"]),
        high=float(row["High"]),
        low=float(row["Low"]),
        close=float(row["Close"]),
        volume=int(row.get("Volume", 0)),
        source="yfinance",
    )


class YFinanceProvider(DataProvider):
    """yfinance wrapper — default provider for historical / backtesting OHLCV."""

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
        use_max = _is_daily_max_request(timeframe, start)

        df = await _fetch_with_retry(
            symbol,
            interval,
            use_max,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
        )

        if df is None or df.empty:
            logger.info("yfinance_no_data", symbol=symbol, timeframe=timeframe)
            return []

        df = df.reset_index()
        ts_col = "Datetime" if "Datetime" in df.columns else "Date"
        records = [
            _row_to_record(row, ts_col, symbol, timeframe, asset_id or 0)
            for _, row in df.iterrows()
        ]
        logger.info("yfinance_ohlcv_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
        info = ticker.info or {}
        now = datetime.now(timezone.utc)
        records = []
        for metric in FUNDAMENTAL_METRICS:
            value = info.get(metric)
            if value is not None:
                fv = float(value)
                if metric == "dividendYield":
                    fv = _normalize_dividend_yield_from_yahoo(fv)
                records.append(FundamentalRecord(
                    time=now,
                    asset_id=asset_id,
                    metric_name=metric,
                    value=fv,
                    source=self.name,
                ))
        logger.info("yfinance_fundamentals_fetched", symbol=symbol, count=len(records))
        return records

    async def fetch_financial_statements(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        loop = asyncio.get_event_loop()
        dfs = await loop.run_in_executor(None, _fetch_statements_sync, symbol)
        records: list[FundamentalRecord] = []
        for stmt_type, df in dfs.items():
            records.extend(_df_to_fundamental_records(df, stmt_type, asset_id, self.name))
        logger.info("yfinance_statements_fetched", symbol=symbol, count=len(records))
        return records

    async def fetch_company_profile(self, symbol: str) -> dict:
        loop = asyncio.get_event_loop()
        profile = await loop.run_in_executor(None, _fetch_profile_sync, symbol)
        logger.info("yfinance_profile_fetched", symbol=symbol)
        return profile
