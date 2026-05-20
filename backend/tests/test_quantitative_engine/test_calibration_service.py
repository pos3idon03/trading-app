"""Tests for calibration_service: mu propagation and last_price population."""
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from dtos.simulation_dto import CalibratedModelParams


def _make_ohlcv_df(prices: np.ndarray) -> pd.DataFrame:
    from datetime import datetime, timedelta, timezone

    n = len(prices)
    dates = [datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(n)]
    return pd.DataFrame({
        "time": dates,
        "open": prices * 0.999,
        "high": prices * 1.005,
        "low": prices * 0.995,
        "close": prices,
        "volume": np.ones(n, dtype=int) * 1_000_000,
        "source": "test",
    })


@pytest.fixture
def trending_prices() -> np.ndarray:
    """500-bar upward-trending price series."""
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0005, 0.015, 500)
    return 100.0 * np.cumprod(1 + returns)


@pytest.mark.asyncio
async def test_calibrated_params_contains_nonzero_mu(trending_prices):
    """Calibration must populate mu from historical prices, not leave it at 0."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    df = _make_ohlcv_df(trending_prices)

    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        result = await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")

    assert isinstance(result, CalibratedModelParams)
    assert result.vasicek.mu != 0.0


@pytest.mark.asyncio
async def test_calibrated_params_last_price_matches_series_end(trending_prices):
    """last_price must equal the final close bar in the calibration window."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    df = _make_ohlcv_df(trending_prices)

    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        result = await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")

    assert result.last_price == pytest.approx(float(trending_prices[-1]))


@pytest.mark.asyncio
async def test_calibrated_params_last_price_is_positive(trending_prices):
    """last_price must always be a positive float for valid price series."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    df = _make_ohlcv_df(trending_prices)

    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        result = await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")

    assert result.last_price > 0.0


def test_merton_skips_ou_on_short_window():
    """Merton-only calibration must not require OU deviation bars."""
    from datetime import datetime, timezone

    from features.quantitative_engine.calibration_service import calibrate_from_prices

    prices = np.linspace(100, 105, 35)
    now = datetime(2024, 6, 1, tzinfo=timezone.utc)
    result = calibrate_from_prices(
        prices, "15m", now, now, ou_ma_window=20, model_type="merton",
    )
    assert result.merton is not None
    assert result.ou_deviation is None


@pytest.mark.asyncio
async def test_calibrated_params_raises_on_short_series():
    """Fewer than 30 rows must raise ValueError."""
    from features.quantitative_engine.calibration_service import calibrate_model_for_asset

    prices = np.linspace(100, 110, 10)
    df = _make_ohlcv_df(prices)

    mock_session = AsyncMock()
    with patch("features.quantitative_engine.calibration_service.get_ohlcv", return_value=df):
        with pytest.raises(ValueError, match="Insufficient data"):
            await calibrate_model_for_asset(mock_session, asset_id=1, timeframe="1d")
