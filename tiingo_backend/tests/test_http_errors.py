import httpx
import pytest

from utils.http_errors import format_external_api_error, redact_secrets


def test_redact_secrets_strips_api_key_query_param():
    raw = (
        "Client error for url "
        "'https://api.stlouisfed.org/fred/series/observations?api_key=secret123&file_type=json'"
    )
    redacted = redact_secrets(raw, secret_values=["secret123"])
    assert "secret123" not in redacted
    assert "api_key=[REDACTED]" in redacted


def test_format_external_api_error_omits_url_for_http_status():
    request = httpx.Request(
        "GET",
        "https://api.stlouisfed.org/fred/series/observations?api_key=hidden",
    )
    response = httpx.Response(400, request=request)
    exc = httpx.HTTPStatusError("bad", request=request, response=response)
    message = format_external_api_error(exc, context="series T10Y2Y", secret_values=["hidden"])
    assert "api_key=" not in message
    assert "hidden" not in message
    assert "HTTP 400" in message
    assert "series T10Y2Y" in message


@pytest.mark.asyncio
async def test_macro_backfill_job_result_never_contains_api_key():
    from unittest.mock import AsyncMock, patch

    from features.fred.macro_orchestrator import backfill_series

    session = AsyncMock()
    session.commit = AsyncMock()

    with patch(
        "features.fred.macro_orchestrator.seed_catalog",
        new=AsyncMock(return_value=0),
    ), patch(
        "features.fred.macro_orchestrator._ingest_series",
        new=AsyncMock(side_effect=RuntimeError(
            "Client error for url 'https://api.stlouisfed.org?api_key=leaked'"
        )),
    ):
        results = await backfill_series(session, ["T10Y2Y"], job_id=None)

    assert results["T10Y2Y"]["status"] == "error"
    error = results["T10Y2Y"]["error"]
    assert "leaked" not in error
    assert "api_key=leaked" not in error
    assert "api_key=[REDACTED]" in error or "HTTP" in error
