"""DAL for trading strategy cards and their linked algo strategies."""
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.strategy_builder import StrategyBacktest, TradingStrategy
from utils.logging import get_logger

logger = get_logger(__name__)


async def create_strategy(session: AsyncSession, asset_id: int) -> TradingStrategy:
    """Create a new strategy card for an asset. Raises if one already exists."""
    strategy = TradingStrategy(asset_id=asset_id, is_active=True)
    session.add(strategy)
    await session.flush()
    await session.refresh(strategy)
    return strategy


async def get_or_create_strategy(session: AsyncSession, asset_id: int) -> TradingStrategy:
    """Return existing strategy for asset_id, creating one if absent."""
    existing = await get_strategy_by_asset(session, asset_id)
    if existing is not None:
        return existing
    return await create_strategy(session, asset_id)


async def get_strategy(session: AsyncSession, strategy_id: int) -> Optional[TradingStrategy]:
    return await session.get(TradingStrategy, strategy_id)


async def get_strategy_by_asset(
    session: AsyncSession, asset_id: int
) -> Optional[TradingStrategy]:
    stmt = select(TradingStrategy).where(TradingStrategy.asset_id == asset_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def list_strategies(session: AsyncSession) -> list[dict]:
    """Return all active strategies joined with asset symbol/name."""
    query = text("""
        SELECT
            ts.id          AS strategy_id,
            ts.asset_id,
            ts.is_active,
            ts.mc_buy_prob_positive,
            ts.mc_sell_prob_positive,
            ts.ai_buy_conviction,
            ts.ai_sell_conviction,
            ts.ai_buy_sentiment,
            ts.ai_sell_sentiment,
            ts.ai_buy_macro,
            ts.ai_sell_macro,
            ts.combination_mode,
            ts.algo_timeframe,
            ts.auto_trading_enabled,
            ts.auto_trading_started,
            ts.max_amount_per_position,
            ts.max_pct_of_capital,
            ts.created_at,
            ts.updated_at,
            a.symbol,
            a.name         AS asset_name
        FROM trading_strategies ts
        JOIN assets a ON a.id = ts.asset_id
        WHERE ts.is_active = TRUE
        ORDER BY a.symbol ASC
    """)
    result = await session.execute(query)
    return [dict(r) for r in result.mappings().all()]


async def delete_strategy(session: AsyncSession, strategy_id: int) -> bool:
    strategy = await session.get(TradingStrategy, strategy_id)
    if strategy is None:
        return False
    await session.delete(strategy)
    return True


async def update_thresholds(
    session: AsyncSession,
    strategy_id: int,
    updates: dict[str, Any],
) -> Optional[TradingStrategy]:
    """Partial update of threshold/configuration columns. Returns updated record or None."""
    strategy = await session.get(TradingStrategy, strategy_id)
    if strategy is None:
        return None
    allowed = {
        "mc_buy_prob_positive", "mc_sell_prob_positive",
        "ai_buy_conviction", "ai_sell_conviction",
        "ai_buy_sentiment", "ai_sell_sentiment",
        "ai_buy_macro", "ai_sell_macro",
        "combination_mode", "algo_timeframe",
        "auto_trading_enabled",
    }
    for key, value in updates.items():
        if key in allowed:
            setattr(strategy, key, value)
    await session.flush()
    await session.refresh(strategy)
    return strategy


async def update_position_sizing(
    session: AsyncSession,
    strategy_id: int,
    started: bool,
    max_amount: Optional[float],
    max_pct: Optional[float],
) -> Optional[TradingStrategy]:
    """Set auto_trading_started and position sizing fields."""
    strategy = await session.get(TradingStrategy, strategy_id)
    if strategy is None:
        return None
    strategy.auto_trading_started = started
    if max_amount is not None:
        strategy.max_amount_per_position = max_amount
    if max_pct is not None:
        strategy.max_pct_of_capital = max_pct
    await session.flush()
    await session.refresh(strategy)
    return strategy


async def list_auto_trading_assets(session: AsyncSession) -> list[dict]:
    """Return rows for all auto-trading-enabled strategies with latest MC and AI values."""
    query = text("""
        SELECT
            ts.id                       AS strategy_id,
            ts.asset_id,
            a.symbol,
            a.name                      AS asset_name,
            a.asset_type,
            ts.mc_buy_prob_positive,
            ts.mc_sell_prob_positive,
            ts.ai_buy_conviction,
            ts.ai_sell_conviction,
            ts.ai_buy_sentiment,
            ts.ai_sell_sentiment,
            ts.ai_buy_macro,
            ts.ai_sell_macro,
            ts.combination_mode,
            ts.algo_timeframe,
            ts.auto_trading_started,
            ts.max_amount_per_position,
            ts.max_pct_of_capital,
            -- Latest Monte Carlo simulation stats
            (
                SELECT result_summary->>'prob_positive_return'
                FROM simulations s
                WHERE s.asset_id = ts.asset_id
                  AND s.status = 'done'
                ORDER BY s.created_at DESC
                LIMIT 1
            )::double precision          AS mc_prob_positive,
            -- Latest AI Agent scores
            (
                SELECT conviction_score
                FROM agent_analyses aa
                WHERE aa.asset_id = ts.asset_id
                  AND aa.status = 'done'
                ORDER BY aa.created_at DESC
                LIMIT 1
            )                            AS ai_conviction,
            (
                SELECT sentiment_score
                FROM agent_analyses aa
                WHERE aa.asset_id = ts.asset_id
                  AND aa.status = 'done'
                ORDER BY aa.created_at DESC
                LIMIT 1
            )                            AS ai_sentiment,
            (
                SELECT macro_score
                FROM agent_analyses aa
                WHERE aa.asset_id = ts.asset_id
                  AND aa.status = 'done'
                ORDER BY aa.created_at DESC
                LIMIT 1
            )                            AS ai_macro
        FROM trading_strategies ts
        JOIN assets a ON a.id = ts.asset_id
        WHERE ts.auto_trading_enabled = TRUE
          AND ts.is_active = TRUE
        ORDER BY a.symbol ASC
    """)
    result = await session.execute(query)
    return [dict(r) for r in result.mappings().all()]


async def attach_algo(
    session: AsyncSession,
    strategy_id: int,
    strategy_name: str,
    params: Optional[dict],
) -> StrategyBacktest:
    """Attach an algo strategy definition to a strategy card.

    Replaces an existing entry for the same strategy_name (upsert on conflict).
    """
    stmt = (
        pg_insert(StrategyBacktest)
        .values(strategy_id=strategy_id, strategy_name=strategy_name, params=params)
        .on_conflict_do_nothing(constraint="strategy_backtests_strategy_id_strategy_name_key")
    )
    await session.execute(stmt)
    await session.flush()

    link = await _get_link_by_name(session, strategy_id, strategy_name)
    return link


async def detach_algo(
    session: AsyncSession,
    strategy_id: int,
    algo_attachment_id: int,
) -> bool:
    """Remove an algo attachment by its primary key."""
    link = await session.get(StrategyBacktest, algo_attachment_id)
    if link is None or link.strategy_id != strategy_id:
        return False
    await session.delete(link)
    return True


async def get_linked_algos(session: AsyncSession, strategy_id: int) -> list[dict]:
    """Return algo strategy definitions linked to this strategy card."""
    query = text("""
        SELECT
            sb.id            AS algo_attachment_id,
            sb.added_at,
            sb.strategy_name,
            sb.params
        FROM strategy_backtests sb
        WHERE sb.strategy_id = :strategy_id
        ORDER BY sb.added_at DESC
    """)
    result = await session.execute(query, {"strategy_id": strategy_id})
    return [dict(r) for r in result.mappings().all()]


async def _get_link_by_name(
    session: AsyncSession, strategy_id: int, strategy_name: str
) -> Optional[StrategyBacktest]:
    stmt = select(StrategyBacktest).where(
        StrategyBacktest.strategy_id == strategy_id,
        StrategyBacktest.strategy_name == strategy_name,
    )
    result = await session.execute(stmt)
    return result.scalars().first()
