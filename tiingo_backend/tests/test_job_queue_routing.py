from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.worker.queue_routing import is_heavy_job, resolve_arq_queue_name
from features.worker.tasks import enqueue_ingestion_job


@pytest.mark.parametrize(
    ("job_type", "expected_heavy"),
    [
        ("foundation_backtest", True),
        ("foundation_preview", True),
        ("ml_train", True),
        ("ml_backtest", True),
        ("ml_label_search", True),
        ("news_sentiment", True),
        ("execution_deployment_cycle", False),
        ("execution_deployment_reconciliation", False),
        ("deployment_market_data_refresh", False),
        ("ohlcv_backfill", False),
        ("news_ingest", False),
        ("news_sentiment_enrichment", False),
        ("macro_refresh", False),
    ],
)
def test_is_heavy_job(job_type: str, expected_heavy: bool) -> None:
    assert is_heavy_job(job_type) is expected_heavy


def test_resolve_arq_queue_name_heavy() -> None:
    assert resolve_arq_queue_name("foundation_backtest") == "heavy"


def test_resolve_arq_queue_name_default() -> None:
    assert resolve_arq_queue_name("execution_deployment_cycle") is None


@pytest.mark.asyncio
async def test_enqueue_heavy_job_uses_heavy_queue() -> None:
    session = AsyncMock()
    job_id = uuid4()
    mock_pool = AsyncMock()

    with patch("features.worker.tasks.get_arq_pool", new=AsyncMock(return_value=mock_pool)):
        await enqueue_ingestion_job(session, job_id, "foundation_backtest", {"symbol": "IBM"})

    session.commit.assert_awaited_once()
    mock_pool.enqueue_job.assert_awaited_once_with(
        "run_ingestion_job",
        str(job_id),
        "foundation_backtest",
        {"symbol": "IBM"},
        _queue_name="heavy",
    )


@pytest.mark.asyncio
async def test_enqueue_light_job_uses_default_queue() -> None:
    session = AsyncMock()
    job_id = uuid4()
    mock_pool = AsyncMock()

    with patch("features.worker.tasks.get_arq_pool", new=AsyncMock(return_value=mock_pool)):
        await enqueue_ingestion_job(
            session,
            job_id,
            "execution_deployment_cycle",
            {},
        )

    mock_pool.enqueue_job.assert_awaited_once_with(
        "run_ingestion_job",
        str(job_id),
        "execution_deployment_cycle",
        {},
    )


@pytest.mark.asyncio
async def test_enqueue_ml_train_uses_heavy_queue() -> None:
    session = AsyncMock()
    job_id = uuid4()
    mock_pool = AsyncMock()

    with patch("features.worker.tasks.get_arq_pool", new=AsyncMock(return_value=mock_pool)):
        await enqueue_ingestion_job(session, job_id, "ml_train", {"symbol": "AAPL"})

    mock_pool.enqueue_job.assert_awaited_once_with(
        "run_ingestion_job",
        str(job_id),
        "ml_train",
        {"symbol": "AAPL"},
        _queue_name="heavy",
    )
