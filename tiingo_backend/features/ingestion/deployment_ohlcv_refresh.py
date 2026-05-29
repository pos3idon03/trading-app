from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import instrument_dal, trading_deployment_dal
from dtos.market_data_dto import OHLCVBackfillRequest
from features.execution.deployment_timeframes import (
    FetchTarget,
    ingest_source_for_asset,
    native_fetch_timeframe,
    needs_4h_derivation,
    validate_execution_timeframe,
)
from features.ingestion.ohlcv_orchestrator import incremental_backfill_symbol_timeframe
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeploymentFetchPlan:
    targets: list[FetchTarget] = field(default_factory=list)
    derive_4h_symbols: set[str] = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not self.targets


def _fetch_key(target: FetchTarget) -> tuple[str, str, str]:
    return (target.symbol, target.native_timeframe, target.source)


def build_fetch_targets(requirements: list[dict]) -> DeploymentFetchPlan:
    seen: set[tuple[str, str, str]] = set()
    targets: list[FetchTarget] = []
    derive_4h_symbols: set[str] = set()

    for row in requirements:
        deployment_tf = row["timeframe"]
        validate_execution_timeframe(deployment_tf)
        native_tf = native_fetch_timeframe(deployment_tf)
        source = ingest_source_for_asset(row.get("asset_type") or "stock", native_tf)
        target = FetchTarget(
            symbol=row["symbol"],
            native_timeframe=native_tf,
            source=source,
            derive_4h=needs_4h_derivation(deployment_tf),
        )
        key = _fetch_key(target)
        if key not in seen:
            seen.add(key)
            targets.append(target)
        if target.derive_4h:
            derive_4h_symbols.add(row["symbol"])

    return DeploymentFetchPlan(targets=targets, derive_4h_symbols=derive_4h_symbols)


async def build_deployment_fetch_plan(
    session: AsyncSession,
    *,
    deployment_timeframes: set[str] | None = None,
) -> DeploymentFetchPlan:
    requirements = await trading_deployment_dal.list_active_deployment_requirements(session)
    if not requirements:
        return DeploymentFetchPlan()

    if deployment_timeframes is not None:
        requirements = [row for row in requirements if row["timeframe"] in deployment_timeframes]
        if not requirements:
            return DeploymentFetchPlan()

    return build_fetch_targets(requirements)


async def refresh_deployment_ohlcv(
    session: AsyncSession,
    plan: DeploymentFetchPlan,
) -> list[dict]:
    if plan.is_empty:
        return []

    settings = get_settings()
    request = OHLCVBackfillRequest(symbols=[], timeframes=[], sources=[])
    end = datetime.now(timezone.utc)
    results: list[dict] = []

    for target in plan.targets:
        inst = await instrument_dal.get_by_symbol(session, target.symbol)
        if not inst:
            results.append(
                {"symbol": target.symbol, "status": "error", "error": "not found"},
            )
            continue

        try:
            inserted, error = await incremental_backfill_symbol_timeframe(
                session,
                symbol=target.symbol,
                instrument_id=inst["id"],
                ticker=inst.get("tiingo_ticker") or target.symbol,
                native_timeframe=target.native_timeframe,
                source=target.source,
                asset_type=inst["asset_type"],
                request=request,
                end=end,
                intraday_days=settings.iex_backfill_days,
                derive_4h=target.symbol in plan.derive_4h_symbols
                and target.native_timeframe == "1h",
            )
            row: dict = {
                "symbol": target.symbol,
                "timeframe": target.native_timeframe,
                "source": target.source,
                "inserted": inserted,
                "status": "ok" if not error else "partial",
            }
            if error:
                row["error"] = error
            results.append(row)
        except Exception as exc:
            logger.error(
                "deployment_ohlcv_refresh_error",
                symbol=target.symbol,
                timeframe=target.native_timeframe,
                error=str(exc),
            )
            results.append(
                {
                    "symbol": target.symbol,
                    "timeframe": target.native_timeframe,
                    "status": "error",
                    "error": str(exc),
                },
            )

    return results


async def refresh_single_deployment_ohlcv(
    session: AsyncSession,
    deployment: dict,
) -> list[dict]:
    inst = await instrument_dal.get_by_symbol(session, deployment["symbol"])
    if not inst:
        return [{"symbol": deployment["symbol"], "status": "error", "error": "not found"}]
    plan = build_fetch_targets(
        [
            {
                "symbol": deployment["symbol"],
                "timeframe": deployment["timeframe"],
                "asset_type": inst.get("asset_type") or "stock",
            },
        ],
    )
    return await refresh_deployment_ohlcv(session, plan)
