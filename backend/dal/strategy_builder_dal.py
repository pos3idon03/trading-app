"""DAL for trading strategy cards and their linked backtest results."""
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


async def attach_backtest(
    session: AsyncSession, strategy_id: int, backtest_id: int
) -> StrategyBacktest:
    """Link a backtest to a strategy; no-op if already linked."""
    stmt = (
        pg_insert(StrategyBacktest)
        .values(strategy_id=strategy_id, backtest_id=backtest_id)
        .on_conflict_do_nothing(constraint="strategy_backtests_strategy_id_backtest_id_key")
    )
    await session.execute(stmt)
    await session.flush()

    link = await _get_link(session, strategy_id, backtest_id)
    return link


async def detach_backtest(
    session: AsyncSession, strategy_id: int, backtest_id: int
) -> bool:
    link = await _get_link(session, strategy_id, backtest_id)
    if link is None:
        return False
    await session.delete(link)
    return True


async def get_linked_backtests(session: AsyncSession, strategy_id: int) -> list[dict]:
    """Return backtest summaries linked to this strategy."""
    query = text("""
        SELECT
            sb.backtest_id,
            sb.added_at,
            br.strategy_name,
            br.total_return,
            br.sharpe_ratio,
            br.max_drawdown,
            br.win_rate,
            br.num_trades
        FROM strategy_backtests sb
        JOIN backtest_results br ON br.id = sb.backtest_id
        WHERE sb.strategy_id = :strategy_id
        ORDER BY sb.added_at DESC
    """)
    result = await session.execute(query, {"strategy_id": strategy_id})
    return [dict(r) for r in result.mappings().all()]


async def _get_link(
    session: AsyncSession, strategy_id: int, backtest_id: int
) -> Optional[StrategyBacktest]:
    stmt = select(StrategyBacktest).where(
        StrategyBacktest.strategy_id == strategy_id,
        StrategyBacktest.backtest_id == backtest_id,
    )
    result = await session.execute(stmt)
    return result.scalars().first()
