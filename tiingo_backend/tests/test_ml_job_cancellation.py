from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from features.ml import job_checkpoints, job_runner
from utils.exceptions import JobCancelledError


@pytest.mark.asyncio
async def test_checkpoint_ml_job_noop_without_job_id():
    session = AsyncMock()
    await job_checkpoints.checkpoint_ml_job(session, None, 50)
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_checkpoint_ml_job_updates_progress_and_commits():
    session = AsyncMock()
    job_id = uuid4()

    with patch(
        "features.ml.job_checkpoints.job_dal.update_job_progress",
        new=AsyncMock(),
    ) as update_progress:
        await job_checkpoints.checkpoint_ml_job(session, job_id, 42)

    update_progress.assert_awaited_once_with(session, job_id, 42)
    session.commit.assert_awaited_once()


def test_progress_in_band_maps_done_to_range():
    assert job_checkpoints.progress_in_band(10, 50, 0, 4) == 10
    assert job_checkpoints.progress_in_band(10, 50, 2, 4) == 30
    assert job_checkpoints.progress_in_band(10, 50, 4, 4) == 50
    assert job_checkpoints.progress_in_band(10, 50, 0, 0) == 50


@pytest.mark.asyncio
async def test_execute_ml_label_search_propagates_cancellation():
    session = AsyncMock()
    job_id = uuid4()

    with patch(
        "features.ml.job_runner.search_ml_labels_for_symbol",
        new=AsyncMock(side_effect=JobCancelledError()),
    ), patch(
        "features.ml.job_runner.checkpoint_ml_job",
        new=AsyncMock(),
    ):
        with pytest.raises(JobCancelledError):
            await job_runner.execute_ml_job(
                session,
                "ml_label_search",
                {
                    "symbol": "BTC-USD",
                    "params": {},
                    "timeframe": "1h",
                    "label_mode": "binary",
                    "horizons": [5],
                    "thresholds": [0.01],
                },
                job_id=job_id,
            )


@pytest.mark.asyncio
async def test_search_ml_labels_checks_cancellation_between_combos():
    from features.ml import orchestrator

    session = AsyncMock()
    job_id = uuid4()
    instrument = {"id": 1, "symbol": "BTC-USD", "asset_type": "crypto"}

    with patch(
        "features.ml.orchestrator.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "features.ml.orchestrator.validate_ml_params",
        return_value={"train_bars": 10, "test_bars": 5, "step_bars": 5, "label_horizon": 5},
    ), patch(
        "features.ml.orchestrator._load_bars_and_features",
        new=AsyncMock(return_value=([{"close": 1}] * 20, [], [[]] * 20, [], [], [], [], [], [])),
    ), patch(
        "features.ml.orchestrator.asyncio.to_thread",
        new=AsyncMock(return_value={"f1_macro": 0.5, "accuracy": 0.5}),
    ), patch(
        "features.ml.job_checkpoints.checkpoint_ml_job",
        new=AsyncMock(side_effect=[None, JobCancelledError()]),
    ) as checkpoint:
        with pytest.raises(JobCancelledError):
            await orchestrator.search_ml_labels_for_symbol(
                session,
                symbol="BTC-USD",
                params={},
                timeframe="1h",
                start=None,
                end=None,
                label_mode="binary",
                horizons=[5, 10],
                thresholds=[0.01],
                model_types=["ml_logistic"],
                job_id=job_id,
            )

    assert checkpoint.await_count == 2


@pytest.mark.asyncio
async def test_search_ml_thresholds_checks_cancellation_between_combos():
    from features.ml import orchestrator

    session = AsyncMock()
    job_id = uuid4()
    instrument = {"id": 1, "symbol": "BTC-USD", "asset_type": "crypto"}
    walk_forward = AsyncMock(
        probabilities=[0.6, 0.4],
        class_predictions=[1, 0],
        class_probabilities=[[0.4, 0.6], [0.6, 0.4]],
        oos_y_true=[1, 0],
        oos_y_proba=[[0.4, 0.6], [0.6, 0.4]],
    )
    combo_result = {"f1_macro": 0.5, "f1": 0.5}

    with patch(
        "features.ml.orchestrator.instrument_dal.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "features.ml.orchestrator.validate_ml_params",
        return_value={
            "train_bars": 10,
            "test_bars": 5,
            "step_bars": 5,
            "label_horizon": 5,
            "label_mode": "binary",
        },
    ), patch(
        "features.ml.orchestrator._load_bars_and_features",
        new=AsyncMock(return_value=([{"close": 1}] * 20, [], [[]] * 20, [], [], [], [], [], [])),
    ), patch(
        "features.ml.orchestrator.build_labels_for_ml_params",
        return_value=[1] * 20,
    ), patch(
        "features.ml.orchestrator.asyncio.to_thread",
        new=AsyncMock(side_effect=[walk_forward, combo_result, combo_result, combo_result, combo_result]),
    ), patch(
        "features.ml.job_checkpoints.checkpoint_ml_job",
        new=AsyncMock(side_effect=[None, None, JobCancelledError()]),
    ) as checkpoint:
        with pytest.raises(JobCancelledError):
            await orchestrator.search_ml_thresholds_for_symbol(
                session,
                symbol="BTC-USD",
                model_type="ml_logistic",
                params={},
                timeframe="1h",
                start=None,
                end=None,
                buy_thresholds=[0.7, 0.8],
                sell_thresholds=[0.3, 0.4],
                job_id=job_id,
            )

    assert checkpoint.await_count == 3


@pytest.mark.parametrize(
    ("job_type", "params", "orchestrator_fn"),
    [
        (
            "ml_train",
            {
                "symbol": "BTC-USD",
                "model_type": "ml_logistic",
                "params": {},
                "timeframe": "1h",
            },
            "train_ml_model_for_symbol",
        ),
        (
            "ml_backtest",
            {
                "symbol": "BTC-USD",
                "model_type": "ml_logistic",
                "params": {},
                "timeframe": "1h",
            },
            "run_ml_backtest_for_symbol",
        ),
        (
            "ml_threshold_search",
            {
                "symbol": "BTC-USD",
                "model_type": "ml_logistic",
                "params": {},
                "timeframe": "1h",
                "buy_thresholds": [0.7],
                "sell_thresholds": [0.3],
            },
            "search_ml_thresholds_for_symbol",
        ),
        (
            "ml_hyperparameter_search",
            {
                "symbol": "BTC-USD",
                "model_type": "ml_logistic",
                "params": {},
                "timeframe": "1h",
            },
            "search_ml_hyperparameters_for_symbol",
        ),
        (
            "ml_training_export",
            {
                "symbol": "BTC-USD",
                "params": {},
                "timeframe": "1h",
            },
            "export_training_data_for_symbol",
        ),
        (
            "ml_workbook_export",
            {
                "symbol": "BTC-USD",
                "params": {},
                "timeframe": "1h",
            },
            "export_workbook_for_symbol",
        ),
    ],
)
@pytest.mark.asyncio
async def test_execute_ml_jobs_pass_job_id(job_type, params, orchestrator_fn):
    session = AsyncMock()
    job_id = uuid4()
    if job_type == "ml_train":
        expected = {
            "id": uuid4(),
            "name": "test-model",
            "model_type": "ml_logistic",
            "feature_mode": "prices_only",
            "train_metrics": {},
            "feature_schema": {},
            "created_at": datetime.now(timezone.utc),
        }
    elif job_type == "ml_backtest":
        expected = {
            "id": uuid4(),
            "symbol": "BTC-USD",
            "strategy": "ml_logistic",
            "status": "completed",
            "metrics": {},
        }
    else:
        expected = {"ok": True}

    with patch(
        f"features.ml.job_runner.{orchestrator_fn}",
        new=AsyncMock(return_value=expected),
    ) as orchestrator_call, patch(
        "features.ml.job_runner.checkpoint_ml_job",
        new=AsyncMock(),
    ):
        await job_runner.execute_ml_job(
            session,
            job_type,
            params,
            job_id=job_id,
        )

    assert orchestrator_call.await_args.kwargs["job_id"] == job_id
