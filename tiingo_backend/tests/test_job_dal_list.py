from dal.job_dal import _to_dict
from models.ingestion_job import IngestionJob


def test_to_dict_omits_result_when_disabled():
    row = IngestionJob(
        job_type="ml_backtest",
        status="completed",
        progress=100,
        params={"symbol": "AAPL"},
        result={"equity_curve": [{"date": "2020-01-01", "equity": 1.0}] * 5000},
    )
    full = _to_dict(row, include_result=True)
    slim = _to_dict(row, include_result=False)
    assert "result" in full
    assert "result" not in slim
    assert slim["job_type"] == "ml_backtest"
