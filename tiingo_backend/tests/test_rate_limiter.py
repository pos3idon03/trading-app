import pytest

from utils.rate_limiter import RateLimitExceeded


def test_rate_limit_exception():
    exc = RateLimitExceeded("limit")
    assert "limit" in str(exc)
