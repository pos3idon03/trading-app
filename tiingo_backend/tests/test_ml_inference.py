from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_inference_run_returns_400_for_schema_mismatch():
    with patch(
        "routes.backtest_ml.run_ml_backtest_for_symbol",
        new=AsyncMock(
            side_effect=ValueError(
                "Feature schema mismatch for inference: expected 3 features"
            )
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/ml/run",
                json={
                    "symbol": "AAPL",
                    "model_type": "ml_logistic",
                    "params": {"model_id": str(uuid4())},
                },
            )

    assert resp.status_code == 400
    assert "schema mismatch" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_inference_run_accepts_model_id():
    run_id = uuid4()
    mock_result = {
        "id": run_id,
        "symbol": "AAPL",
        "strategy": "ml_logistic",
        "status": "completed",
        "metrics": {
            "total_return_pct": 5.0,
            "benchmark_return_pct": 10.0,
            "alpha_pct": -5.0,
            "cagr_pct": 2.0,
            "max_drawdown_pct": 3.0,
            "sharpe_ratio": 0.5,
            "sortino_ratio": 0.7,
            "profit_factor": 1.2,
            "calmar_ratio": 0.67,
            "win_rate_pct": 50.0,
            "trade_count": 3,
            "final_equity": 10500.0,
            "initial_cash": 10000.0,
        },
    }

    with patch(
        "routes.backtest_ml.run_ml_backtest_for_symbol",
        new=AsyncMock(return_value=mock_result),
    ) as mock_run:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            model_id = str(uuid4())
            resp = await client.post(
                "/api/v1/backtest/ml/run",
                json={
                    "symbol": "AAPL",
                    "model_type": "ml_logistic",
                    "params": {"model_id": model_id},
                },
            )

    assert resp.status_code == 200
    call_kwargs = mock_run.await_args.kwargs
    assert call_kwargs["params"]["model_id"] == model_id
