"""DAL for live trading indicators and signals."""
from typing import Optional

from sqlalchemy import desc, select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from models.live_trading import LiveIndicator, TradingSignal
from utils.logging import get_logger

logger = get_logger(__name__)


async def create_indicator(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    rsi: float | None = None,
    macd: float | None = None,
    macd_signal: float | None = None,
    macd_histogram: float | None = None,
    bb_upper: float | None = None,
    bb_middle: float | None = None,
    bb_lower: float | None = None,
    vwap: float | None = None,
    close_price: float | None = None,
    volume: int | None = None,
    raw_data: dict | None = None,
) -> int:
    record = LiveIndicator(
        symbol=symbol,
        timeframe=timeframe,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        vwap=vwap,
        close_price=close_price,
        volume=volume,
        raw_data=raw_data,
    )
    session.add(record)
    await session.flush()
    return record.id


async def get_latest_indicator(
    session: AsyncSession, symbol: str, timeframe: str,
) -> Optional[LiveIndicator]:
    stmt = (
        select(LiveIndicator)
        .where(LiveIndicator.symbol == symbol, LiveIndicator.timeframe == timeframe)
        .order_by(desc(LiveIndicator.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_signal(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    action: str,
    confidence: float,
    technical_score: float,
    risk_score: float,
    ai_score: float,
    reasoning: str | None = None,
    indicator_snapshot: dict | None = None,
    risk_data: dict | None = None,
    ai_signal: dict | None = None,
) -> int:
    record = TradingSignal(
        symbol=symbol,
        timeframe=timeframe,
        action=action,
        confidence=confidence,
        technical_score=technical_score,
        risk_score=risk_score,
        ai_score=ai_score,
        reasoning=reasoning,
        indicator_snapshot=indicator_snapshot,
        risk_data=risk_data,
        ai_signal=ai_signal,
    )
    session.add(record)
    await session.flush()
    return record.id


async def get_latest_signal(
    session: AsyncSession, symbol: str,
) -> Optional[TradingSignal]:
    stmt = (
        select(TradingSignal)
        .where(TradingSignal.symbol == symbol)
        .order_by(desc(TradingSignal.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_signal_history(
    session: AsyncSession, symbol: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[TradingSignal], int]:
    base = select(TradingSignal)
    count_base = select(sa_func.count(TradingSignal.id))

    if symbol:
        base = base.where(TradingSignal.symbol == symbol)
        count_base = count_base.where(TradingSignal.symbol == symbol)

    count_result = await session.execute(count_base)
    total = count_result.scalar() or 0

    stmt = base.order_by(desc(TradingSignal.created_at)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all()), total
