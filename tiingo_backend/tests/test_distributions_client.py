from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from features.tiingo.distributions_client import (
    _latest_trailing_yield,
    _parse_trailing_yield,
    fetch_distribution_yield,
)


def test_parse_trailing_yield_accepts_decimal_ratio():
    assert _parse_trailing_yield("0.0655") == 6.55
    assert _parse_trailing_yield(0.00394) == 0.39


def test_parse_trailing_yield_rejects_invalid_values():
    assert _parse_trailing_yield(None) is None
    assert _parse_trailing_yield("bad") is None
    assert _parse_trailing_yield(-1.0) is None


def test_latest_trailing_yield_picks_most_recent_date():
    rows = [
        {"date": "2024-01-01", "trailingDiv1Y": "0.01"},
        {"date": "2024-06-01", "trailingDiv1Y": "0.015"},
    ]
    assert _latest_trailing_yield(rows) == 1.5


@pytest.mark.asyncio
async def test_fetch_distribution_yield_returns_latest_value():
    payload = [
        {"date": "2024-01-01", "trailingDiv1Y": "0.008"},
        {"date": "2024-06-01", "trailingDiv1Y": "0.012"},
    ]

    with patch("features.tiingo.distributions_client.get_token", return_value="tok"), patch(
        "features.tiingo.distributions_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = payload
        instance.get = AsyncMock(return_value=resp)

        result = await fetch_distribution_yield("QQQ")

    assert result == 1.2
    instance.get.assert_awaited_once()
    call_kwargs = instance.get.await_args.kwargs
    assert call_kwargs["params"]["columns"] == "trailingDiv1Y"


@pytest.mark.asyncio
async def test_fetch_distribution_yield_returns_none_on_404():
    with patch("features.tiingo.distributions_client.get_token", return_value="tok"), patch(
        "features.tiingo.distributions_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.status_code = 404
        instance.get = AsyncMock(return_value=resp)

        result = await fetch_distribution_yield("UNKNOWN")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_distribution_yield_returns_none_on_empty_payload():
    with patch("features.tiingo.distributions_client.get_token", return_value="tok"), patch(
        "features.tiingo.distributions_client.httpx.AsyncClient"
    ) as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = []
        instance.get = AsyncMock(return_value=resp)

        result = await fetch_distribution_yield("QQQ")

    assert result is None
