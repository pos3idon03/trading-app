"""Periodic auto-trading evaluation loop.

Loads running auto-trading assets, evaluates criteria + algo strategy signals,
combines them per the configured mode, and executes orders when a BUY/SELL
signal is produced.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from dal.execution_dal import create_order, update_order_status
from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv
from dal.strategy_builder_dal import get_linked_algos, list_auto_trading_assets
from features.execution.broker_client import has_position
from features.execution.order_sync import parse_filled_at, wait_for_order_terminal
from features.execution.order_manager import (
    execute_order_plan,
    plan_order_from_signal,
    qty_decimals_for_asset_type,
)
from features.execution.symbol_resolver import _looks_like_yfinance_crypto_pair
from features.execution.portfolio_tracker import sync_portfolio
from features.execution.risk_manager import get_risk_manager
from features.execution.symbol_resolver import to_alpaca_symbol
from features.live_trading.resampler import ResamplingEngine
from features.live_trading.signal_aggregator import AggregatedSignal
from features.live_trading.strategy_signals import (
    MIN_BARS_REQUIRED,
    compute_strategy_signals,
)
from utils.logging import get_logger

logger = get_logger(__name__)

_WEEKLY_LOOKBACK = timedelta(weeks=104)
_DEFAULT_LOOKBACK = timedelta(days=365)


# ---------------------------------------------------------------------------
# Signal evaluation helpers
# ---------------------------------------------------------------------------

def evaluate_criterion(
    value: float | None, buy_threshold: float | None, sell_threshold: float | None,
) -> str:
    if value is None:
        return "NEUTRAL"
    if buy_threshold is not None and value >= buy_threshold:
        return "BUY"
    if sell_threshold is not None and value <= sell_threshold:
        return "SELL"
    return "NEUTRAL"


def build_criteria_signals(asset: dict) -> list[str]:
    """Evaluate MC + AI criteria against thresholds, returning per-criterion signals."""
    return [
        evaluate_criterion(
            asset.get("mc_prob_positive"),
            asset.get("mc_buy_prob_positive"),
            asset.get("mc_sell_prob_positive"),
        ),
        evaluate_criterion(
            asset.get("ai_conviction"),
            asset.get("ai_buy_conviction"),
            asset.get("ai_sell_conviction"),
        ),
        evaluate_criterion(
            asset.get("ai_sentiment"),
            asset.get("ai_buy_sentiment"),
            asset.get("ai_sell_sentiment"),
        ),
        evaluate_criterion(
            asset.get("ai_macro"),
            asset.get("ai_buy_macro"),
            asset.get("ai_sell_macro"),
        ),
    ]


def combine_signals(
    signals: list[str], mode: str,
) -> str:
    """Combine a list of BUY/SELL/NEUTRAL strings using the given combination mode."""
    total = len(signals)
    if total == 0:
        return "NEUTRAL"

    active = [s for s in signals if s != "NEUTRAL"]
    if not active:
        return "NEUTRAL"

    buys = sum(1 for s in active if s == "BUY")
    sells = sum(1 for s in active if s == "SELL")

    if mode == "all":
        if buys == total:
            return "BUY"
        if sells == total:
            return "SELL"
        return "NEUTRAL"

    if mode == "majority":
        if buys > total / 2:
            return "BUY"
        if sells > total / 2:
            return "SELL"
        return "NEUTRAL"

    # 'any'
    if buys > 0:
        return "BUY"
    if sells > 0:
        return "SELL"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# OHLCV helpers
# ---------------------------------------------------------------------------

def _ohlcv_query_args(timeframe: str) -> dict:
    if timeframe == "1w":
        return {"timeframe": "1d", "bucket_interval": timedelta(weeks=1)}
    return {"timeframe": timeframe}


def _df_rows_to_bars(df) -> list:
    bars = []
    for _, row in df.iterrows():
        bars.append(SimpleNamespace(
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume", 0)),
        ))
    return bars


async def _get_bars_for_asset(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    resampler: ResamplingEngine | None,
) -> list:
    """Get bars from resampler first, falling back to DB historical data."""
    if resampler is not None:
        bars = resampler.get_bars(symbol, timeframe)
        if len(bars) >= MIN_BARS_REQUIRED:
            return bars

    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        return []

    now = datetime.now(timezone.utc)
    lookback = _WEEKLY_LOOKBACK if timeframe == "1w" else _DEFAULT_LOOKBACK
    df = await get_ohlcv(session, asset_id, start=now - lookback, end=now, **_ohlcv_query_args(timeframe))
    if df.empty:
        return []
    return _df_rows_to_bars(df)


# ---------------------------------------------------------------------------
# Algo signal extraction from live strategy signals
# ---------------------------------------------------------------------------

async def _get_algo_signals(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    strategy_id: int,
    resampler: ResamplingEngine | None,
) -> list[str]:
    """Run attached algo strategies and return their signals."""
    linked = await get_linked_algos(session, strategy_id)
    if not linked:
        return []

    bars = await _get_bars_for_asset(session, symbol, timeframe, resampler)
    if len(bars) < MIN_BARS_REQUIRED:
        return []

    all_results = compute_strategy_signals(bars, symbol)
    signal_map = {r.strategy: r.signal for r in all_results}

    algo_signals: list[str] = []
    for row in linked:
        name = row["strategy_name"]
        if name.startswith("combo:"):
            params = row.get("params") or {}
            sub_strategies = params.get("strategies", [])
            child_signals = [
                signal_map.get(s["strategy_name"], "NEUTRAL")
                for s in sub_strategies
            ]
            combo_mode = params.get("combination_mode", "majority")
            algo_signals.append(combine_signals(child_signals, combo_mode))
        else:
            algo_signals.append(signal_map.get(name, "NEUTRAL"))

    return algo_signals


def _get_latest_price(bars: list) -> float | None:
    if not bars:
        return None
    last = bars[-1]
    return getattr(last, "close", None)


# ---------------------------------------------------------------------------
# Single-asset evaluation
# ---------------------------------------------------------------------------

async def evaluate_asset(
    session: AsyncSession,
    asset: dict,
    resampler: ResamplingEngine | None = None,
) -> str:
    """Evaluate one auto-trading asset and return the combined signal string."""
    symbol = asset["symbol"]
    timeframe = asset.get("algo_timeframe", "1d")
    mode = asset.get("combination_mode", "all")

    criteria_signals = build_criteria_signals(asset)
    algo_signals = await _get_algo_signals(
        session, symbol, timeframe, asset["strategy_id"], resampler,
    )

    all_signals = criteria_signals + algo_signals
    return combine_signals(all_signals, mode)


# ---------------------------------------------------------------------------
# Order execution for a single asset
# ---------------------------------------------------------------------------

async def _execute_for_asset(
    session: AsyncSession,
    asset: dict,
    combined_signal: str,
    current_price: float,
) -> None:
    """Place an order when the combined signal is BUY or SELL."""
    if combined_signal not in ("BUY", "SELL"):
        return

    yf_symbol = asset["symbol"]
    asset_type = asset.get("asset_type", "stock")
    alpaca_symbol = to_alpaca_symbol(yf_symbol, asset_type)

    if alpaca_symbol is None:
        logger.warning(
            "order_skipped_unsupported_symbol",
            symbol=yf_symbol,
            asset_type=asset_type,
        )
        return

    currently_holding = has_position(alpaca_symbol)

    if combined_signal == "BUY" and currently_holding:
        logger.info(
            "order_skipped_already_in_position",
            symbol=yf_symbol,
            alpaca_symbol=alpaca_symbol,
        )
        return

    if combined_signal == "SELL" and not currently_holding:
        logger.info(
            "order_skipped_no_position_to_sell",
            symbol=yf_symbol,
            alpaca_symbol=alpaca_symbol,
        )
        return

    action = combined_signal
    confidence = 0.75  # base confidence for threshold-driven signals

    signal = AggregatedSignal(
        symbol=alpaca_symbol,
        timeframe=asset.get("algo_timeframe", "1d"),
        action=action,
        confidence=confidence,
        technical_score=0.0,
        risk_score=0.0,
        ai_score=0.0,
        reasoning=f"Auto-trading loop: combined signal = {action}",
    )

    portfolio = sync_portfolio()
    asset_type = asset.get("asset_type") or "stock"
    decimals = qty_decimals_for_asset_type(asset_type)
    if asset_type != "crypto" and _looks_like_yfinance_crypto_pair(yf_symbol):
        decimals = qty_decimals_for_asset_type("crypto")

    plan = plan_order_from_signal(
        signal,
        portfolio,
        current_price,
        max_amount_per_position=asset.get("max_amount_per_position"),
        max_pct_of_capital=asset.get("max_pct_of_capital"),
        qty_decimals=decimals,
    )
    if plan is None:
        logger.info("no_order_plan", symbol=asset["symbol"], action=action)
        return

    order_id = await create_order(
        session,
        symbol=yf_symbol,
        side=plan.side,
        qty=plan.qty,
        order_type=plan.order_type,
        asset_id=asset.get("asset_id"),
    )

    risk_result, order_result = execute_order_plan(plan)
    if order_result is None:
        await update_order_status(
            session, order_id, status="rejected",
            error_message="; ".join(risk_result.violations),
        )
        return

    if order_result.order_id:
        order_result = wait_for_order_terminal(order_result.order_id, order_result)

    await update_order_status(
        session,
        order_id,
        status=order_result.status,
        alpaca_order_id=order_result.order_id,
        filled_price=order_result.filled_price,
        filled_qty=order_result.filled_qty,
        filled_at=parse_filled_at(order_result),
    )
    logger.info(
        "auto_trade_executed",
        symbol=yf_symbol,
        alpaca_symbol=alpaca_symbol,
        side=plan.side,
        qty=plan.qty,
        status=order_result.status,
    )


# ---------------------------------------------------------------------------
# Main loop entry point
# ---------------------------------------------------------------------------

async def run_auto_trading_cycle(
    session: AsyncSession,
    resampler: ResamplingEngine | None = None,
) -> list[dict]:
    """Evaluate all running auto-trading assets and execute orders.

    Returns a summary list of evaluated assets for logging / API response.
    """
    risk_mgr = get_risk_manager()
    if risk_mgr.config.kill_switch_active:
        logger.warning("auto_trading_skipped_kill_switch_active")
        return []

    rows = await list_auto_trading_assets(session)
    running = [r for r in rows if r.get("auto_trading_started")]
    if not running:
        return []

    results: list[dict] = []

    for asset in running:
        symbol = asset["symbol"]
        timeframe = asset.get("algo_timeframe", "1d")
        try:
            combined = await evaluate_asset(session, asset, resampler)

            bars = await _get_bars_for_asset(session, symbol, timeframe, resampler)
            price = _get_latest_price(bars)

            if combined in ("BUY", "SELL") and price is not None and price > 0:
                await _execute_for_asset(session, asset, combined, price)

            results.append({
                "symbol": symbol,
                "signal": combined,
                "price": price,
                "executed": combined in ("BUY", "SELL") and price is not None,
            })
        except Exception as exc:
            logger.error("auto_trading_asset_error", symbol=symbol, error=str(exc))
            results.append({"symbol": symbol, "signal": "ERROR", "error": str(exc)})

    return results
