from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from features.ml.job_checkpoints import checkpoint_ml_job
from features.ml.orchestrator import (
    export_training_data_for_symbol,
    export_workbook_for_symbol,
    preview_ml_data_for_symbol,
    run_ml_backtest_for_symbol,
    search_ml_hyperparameters_for_symbol,
    search_ml_labels_for_symbol,
    search_ml_thresholds_for_symbol,
    train_ml_model_for_symbol,
)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def execute_ml_job(
    session: AsyncSession,
    job_type: str,
    params: dict,
    job_id: UUID | None = None,
) -> dict:
    await checkpoint_ml_job(session, job_id, 5)
    start = _parse_datetime(params.get("start"))
    end = _parse_datetime(params.get("end"))

    if job_type == "ml_data_preview":
        preview = await preview_ml_data_for_symbol(
            session,
            symbol=params["symbol"],
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            model_type=params.get("model_type", "ml_logistic"),
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return preview

    if job_type == "ml_label_search":
        results = await search_ml_labels_for_symbol(
            session,
            symbol=params["symbol"],
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            label_mode=params["label_mode"],
            horizons=params["horizons"],
            thresholds=params["thresholds"],
            model_type=params.get("model_type"),
            model_types=params.get("model_types"),
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return {"results": results}

    if job_type == "ml_training_export":
        payload = await export_training_data_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params.get("model_type", "ml_logistic"),
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            scope=params.get("scope", "all_labeled"),
            sample_size=int(params.get("sample_size", 500)),
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return payload

    if job_type == "ml_workbook_export":
        run_id = params.get("run_id")
        payload = await export_workbook_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params.get("model_type", "ml_logistic"),
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            training_scope=params.get("training_scope", "all_labeled"),
            sample_size=int(params.get("sample_size", 500)),
            run_id=UUID(str(run_id)) if run_id else None,
            data_preview=params.get("data_preview"),
            label_search_results=params.get("label_search_results"),
            threshold_search_results=params.get("threshold_search_results"),
            compare_results=params.get("compare_results"),
            config_snapshot=params.get("config_snapshot"),
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return payload

    if job_type == "ml_threshold_search":
        results = await search_ml_thresholds_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params["model_type"],
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            buy_thresholds=params["buy_thresholds"],
            sell_thresholds=params["sell_thresholds"],
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return {"results": results}

    if job_type == "ml_hyperparameter_search":
        result = await search_ml_hyperparameters_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params["model_type"],
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return result

    if job_type == "ml_train":
        row = await train_ml_model_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params["model_type"],
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            name=params.get("name"),
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "model_type": row["model_type"],
            "feature_mode": row["feature_mode"],
            "train_metrics": row.get("train_metrics") or {},
            "feature_schema": row.get("feature_schema") or {},
            "created_at": row["created_at"].isoformat(),
        }

    if job_type == "ml_backtest":
        result = await run_ml_backtest_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params["model_type"],
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            initial_cash=float(params.get("initial_cash", 10_000)),
            commission_bps=float(params.get("commission_bps", 0)),
            job_id=job_id,
        )
        await checkpoint_ml_job(session, job_id, 100)
        return {
            "run_id": str(result["id"]),
            "id": str(result["id"]),
            "symbol": result["symbol"],
            "model_type": result["strategy"],
            "status": result["status"],
            "metrics": result.get("metrics"),
        }

    raise ValueError(f"Unknown ML job type: {job_type}")
