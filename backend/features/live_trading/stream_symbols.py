"""Resolve app symbols to Alpaca stream channels for live market data."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_type_by_symbol
from features.execution.symbol_resolver import to_alpaca_symbol
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class StreamSymbolEntry:
    app_symbol: str
    alpaca_symbol: str
    channel: str  # "stock" | "crypto"


@dataclass
class StreamPlan:
    entries: list[StreamSymbolEntry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def app_symbols(self) -> list[str]:
        return [e.app_symbol for e in self.entries]

    def stock_alpaca_symbols(self) -> list[str]:
        return [e.alpaca_symbol for e in self.entries if e.channel == "stock"]

    def crypto_alpaca_symbols(self) -> list[str]:
        return [e.alpaca_symbol for e in self.entries if e.channel == "crypto"]

    def app_symbol_set(self) -> frozenset[str]:
        return frozenset(self.app_symbols)


def _normalize_app_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _channel_for(asset_type: str, alpaca_symbol: str) -> str:
    if asset_type == "crypto" or "/" in alpaca_symbol:
        return "crypto"
    return "stock"


async def build_stream_plan(
    session: AsyncSession,
    symbols: list[str],
) -> StreamPlan:
    """Map requested app symbols to Alpaca stock/crypto stream subscriptions."""
    plan = StreamPlan()
    seen: set[str] = set()

    for raw in symbols:
        app_symbol = _normalize_app_symbol(raw)
        if not app_symbol or app_symbol in seen:
            continue
        seen.add(app_symbol)

        asset_type = await get_asset_type_by_symbol(session, app_symbol) or "stock"
        alpaca_symbol = to_alpaca_symbol(app_symbol, asset_type)
        if not alpaca_symbol:
            plan.skipped.append(app_symbol)
            logger.warning("stream_skip_unsupported", symbol=app_symbol, asset_type=asset_type)
            continue

        plan.entries.append(
            StreamSymbolEntry(
                app_symbol=app_symbol,
                alpaca_symbol=alpaca_symbol.upper(),
                channel=_channel_for(asset_type.lower(), alpaca_symbol),
            ),
        )

    return plan
