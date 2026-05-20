"""Orchestrates the four data dimensions for a Strategy Builder card.

Each dimension is fetched independently; failures are captured as error
strings so a single failure does not block the whole card from loading.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dal.strategy_builder_dal import get_linked_algos
from dtos.strategy_builder_dto import (
    AIAgentSummary,
    AlgoStrategySummary,
    FinancialsSummary,
    MonteCarloSummary,
    StrategyFullResponse,
)
from features.strategy_builder.ai_agents_fetcher import get_latest_agent_analysis
from features.strategy_builder.financials_fetcher import get_financials_for_asset
from features.strategy_builder.monte_carlo_runner import get_or_run_merton_for_asset
from models.strategy_builder import TradingStrategy
from utils.logging import get_logger

logger = get_logger(__name__)


async def build_full_strategy_response(
    session: AsyncSession,
    strategy: TradingStrategy,
    symbol: str,
    asset_name: Optional[str],
) -> StrategyFullResponse:
    mc, mc_err = await _fetch_monte_carlo(session, strategy.asset_id)
    ai, ai_err = await _fetch_ai_agents(session, strategy.asset_id)
    fin, fin_err = await _fetch_financials(session, strategy.asset_id, symbol)
    algo = await _fetch_algo_strategies(session, strategy.id)

    return StrategyFullResponse(
        strategy_id=strategy.id,
        asset_id=strategy.asset_id,
        symbol=symbol,
        asset_name=asset_name,
        is_active=strategy.is_active,
        created_at=strategy.created_at,
        mc_buy_prob_positive=strategy.mc_buy_prob_positive,
        mc_sell_prob_positive=strategy.mc_sell_prob_positive,
        ai_buy_conviction=strategy.ai_buy_conviction,
        ai_sell_conviction=strategy.ai_sell_conviction,
        ai_buy_sentiment=strategy.ai_buy_sentiment,
        ai_sell_sentiment=strategy.ai_sell_sentiment,
        ai_buy_macro=strategy.ai_buy_macro,
        ai_sell_macro=strategy.ai_sell_macro,
        combination_mode=strategy.combination_mode,
        algo_timeframe=strategy.algo_timeframe,
        auto_trading_enabled=strategy.auto_trading_enabled,
        auto_trading_started=strategy.auto_trading_started,
        max_amount_per_position=strategy.max_amount_per_position,
        max_pct_of_capital=strategy.max_pct_of_capital,
        monte_carlo=mc,
        ai_agents=ai,
        financials=fin,
        algo_strategies=algo,
        monte_carlo_error=mc_err,
        ai_agents_error=ai_err,
        financials_error=fin_err,
    )


async def _fetch_monte_carlo(
    session: AsyncSession,
    asset_id: int,
) -> tuple[Optional[MonteCarloSummary], Optional[str]]:
    try:
        result = await get_or_run_merton_for_asset(session, asset_id)
        return result, None
    except Exception as exc:
        logger.error("strategy_mc_error", asset_id=asset_id, error=str(exc))
        return None, str(exc)


async def _fetch_ai_agents(
    session: AsyncSession,
    asset_id: int,
) -> tuple[Optional[AIAgentSummary], Optional[str]]:
    try:
        result = await get_latest_agent_analysis(session, asset_id)
        return result, None
    except Exception as exc:
        logger.error("strategy_ai_error", asset_id=asset_id, error=str(exc))
        return None, str(exc)


async def _fetch_financials(
    session: AsyncSession,
    asset_id: int,
    symbol: str,
) -> tuple[Optional[FinancialsSummary], Optional[str]]:
    try:
        result = await get_financials_for_asset(session, asset_id, symbol)
        return result, None
    except Exception as exc:
        logger.error("strategy_fin_error", asset_id=asset_id, error=str(exc))
        return None, str(exc)


async def _fetch_algo_strategies(
    session: AsyncSession,
    strategy_id: int,
) -> list[AlgoStrategySummary]:
    rows = await get_linked_algos(session, strategy_id)
    return [
        AlgoStrategySummary(
            algo_attachment_id=r["algo_attachment_id"],
            strategy_name=r["strategy_name"],
            params=r.get("params"),
            timeframe=r.get("timeframe") or "1d",
            added_at=r["added_at"],
        )
        for r in rows
    ]
