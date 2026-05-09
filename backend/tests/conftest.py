"""Shared pytest fixtures."""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql://test:test@localhost/test")


@pytest.fixture
def sample_prices() -> np.ndarray:
    """Synthetic random-walk price series (500 days)."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0003, 0.015, 500)
    prices = 100 * np.cumprod(1 + returns)
    return prices


@pytest.fixture
def sample_ohlcv_df(sample_prices) -> pd.DataFrame:
    """DataFrame with OHLCV columns derived from sample_prices."""
    import pandas as pd
    from datetime import datetime, timezone, timedelta

    n = len(sample_prices)
    dates = [datetime(2022, 1, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(n)]
    df = pd.DataFrame({
        "time": dates,
        "open": sample_prices * 0.999,
        "high": sample_prices * 1.005,
        "low": sample_prices * 0.995,
        "close": sample_prices,
        "volume": np.random.randint(1_000_000, 10_000_000, n),
        "source": "test",
    })
    return df


@pytest.fixture
def sample_log_returns(sample_prices) -> np.ndarray:
    return np.diff(np.log(sample_prices))
