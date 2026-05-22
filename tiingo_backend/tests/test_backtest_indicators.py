from datetime import datetime, timezone

import pytest

from features.backtesting.indicators import (
    compute_bollinger_bands,
    compute_donchian,
    compute_ema,
    compute_mfi,
    compute_rsi,
    compute_sma,
    compute_stochastic,
)


def test_compute_sma_returns_none_until_period_met():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = compute_sma(values, 3)
    assert result[:2] == [None, None]
    assert result[2] == pytest.approx(2.0)
    assert result[4] == pytest.approx(4.0)


def test_compute_ema_starts_after_period():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = compute_ema(values, 3)
    assert result[0] is None
    assert result[2] == pytest.approx(2.0)
    assert result[4] is not None


def test_compute_rsi_high_when_only_gains():
    values = [float(i) for i in range(1, 20)]
    result = compute_rsi(values, 14)
    assert result[-1] == pytest.approx(100.0)


def test_compute_rsi_empty_values():
    assert compute_rsi([], 14) == []


def test_compute_donchian_uses_prior_bars_only():
    highs = [10.0, 12.0, 11.0, 13.0, 15.0]
    lows = [8.0, 9.0, 8.5, 10.0, 11.0]
    upper, lower = compute_donchian(highs, lows, 3)
    assert upper[:3] == [None, None, None]
    assert upper[3] == pytest.approx(12.0)
    assert lower[3] == pytest.approx(8.0)
    assert upper[4] == pytest.approx(13.0)


def test_compute_bollinger_bands_symmetric():
    values = [float(i) for i in range(1, 11)]
    middle, upper, lower = compute_bollinger_bands(values, 5, 2.0)
    assert middle[4] == pytest.approx(3.0)
    assert upper[4] == pytest.approx(middle[4] + 2.0 * (2.0**0.5))
    assert lower[4] == pytest.approx(middle[4] - 2.0 * (2.0**0.5))


def test_compute_stochastic_range():
    highs = [12.0, 13.0, 14.0, 15.0, 16.0]
    lows = [10.0, 11.0, 12.0, 13.0, 14.0]
    closes = [11.0, 12.0, 13.0, 14.0, 15.0]
    k_values, d_values = compute_stochastic(highs, lows, closes, 3, 2)
    assert k_values[2] == pytest.approx(75.0)
    assert k_values[4] == pytest.approx(75.0)
    assert d_values[3] == pytest.approx(75.0)


def test_compute_mfi_high_when_positive_flow_dominates():
    highs = [11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    lows = [9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    volumes = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    result = compute_mfi(highs, lows, closes, volumes, 3)
    assert result[:3] == [None, None, None]
    assert result[-1] == pytest.approx(100.0)
