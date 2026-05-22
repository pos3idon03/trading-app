import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes import backtest, fundamentals_read, ingestion, instruments, macro, market_data, overview
from utils.logging import configure_logging, get_logger, new_correlation_id

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("tiingo_backend_startup", env=settings.app_env)

    try:
        from db import AsyncSessionLocal
        from features.worker.tasks import create_and_enqueue_job

        async with AsyncSessionLocal() as session:
            await create_and_enqueue_job(session, "macro_seed_catalog", {})
        logger.info("macro_seed_catalog_enqueued")
    except Exception as exc:
        logger.warning("macro_seed_catalog_enqueue_failed", error=str(exc))

    if settings.enable_scheduler:
        from features.scheduler.scheduler import start_scheduler
        start_scheduler()

    if settings.stream_enabled:
        from features.stream import iex_stream
        await iex_stream.start_stream()

    yield

    if settings.enable_scheduler:
        from features.scheduler.scheduler import stop_scheduler
        stop_scheduler()

    from features.stream import iex_stream
    await iex_stream.stop_stream()

    from features.worker.pool import close_arq_pool
    await close_arq_pool()

    logger.info("tiingo_backend_shutdown")


app = FastAPI(
    title="Tiingo Ingestion API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
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
    new_correlation_id()
    start = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - start) * 1000, 2),
    )
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tiingo_backend"}


app.include_router(instruments.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(macro.router, prefix="/api/v1")
app.include_router(fundamentals_read.router, prefix="/api/v1")
app.include_router(market_data.router, prefix="/api/v1")
app.include_router(overview.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
