import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from utils.logging import configure_logging, get_logger, new_correlation_id

from features.ai_agents.llm_provider import configure_litellm  # noqa: E402

settings = get_settings()
configure_logging(settings.log_level)
configure_litellm(settings)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.app_env)

    if settings.enable_scheduler:
        from features.data_ingestion.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
        logger.info("scheduler_enabled")

    yield

    if settings.enable_scheduler:
        from features.data_ingestion.scheduler import stop_scheduler
        stop_scheduler()

    from features.live_trading.websocket_stream import get_stream
    await get_stream().stop()
    logger.info("shutdown")


app = FastAPI(
    title="Trading App API",
    version="1.0.0",
    description="AI-driven automated trading platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    cid = new_correlation_id()
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        correlation_id=cid,
    )
    response.headers["X-Correlation-ID"] = cid
    return response


from routes import ai_agents, auto_trading, backtest, data_ingestion, execution, financials, live_trading, monte_carlo, strategy_builder  # noqa: E402

app.include_router(data_ingestion.router, prefix="/api/v1/data", tags=["Data Ingestion"])
app.include_router(financials.router, prefix="/api/v1/financials", tags=["Financials"])
app.include_router(monte_carlo.router, prefix="/api/v1/simulation", tags=["Simulation"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["Backtesting"])
app.include_router(ai_agents.router, prefix="/api/v1/agents", tags=["AI Agents"])
app.include_router(live_trading.router, prefix="/api/v1/live", tags=["Live Trading"])
app.include_router(execution.router, prefix="/api/v1/execution", tags=["Execution"])
app.include_router(strategy_builder.router, prefix="/api/v1/strategy-builder", tags=["Strategy Builder"])
app.include_router(auto_trading.router, prefix="/api/v1/auto-trading", tags=["Auto-Trading"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "env": settings.app_env}
