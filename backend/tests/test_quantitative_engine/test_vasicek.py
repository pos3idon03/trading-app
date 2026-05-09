"""Tests for Vasicek model parameter estimation."""
import numpy as np
import pytest

from features.quantitative_engine.vasicek import (
    VasicekParams,
    calibrate_vasicek,
    compute_historical_volatility,
    estimate_mean_reversion_params,
)


class TestEstimateMeanReversionParams:
    def test_returns_vasicek_params(self, sample_prices):
        params = estimate_mean_reversion_params(sample_prices)
        assert isinstance(params, VasicekParams)

    def test_k_is_positive(self, sample_prices):
        params = estimate_mean_reversion_params(sample_prices)
        assert params.k > 0

    def test_sigma_is_positive(self, sample_prices):
        params = estimate_mean_reversion_params(sample_prices)
        assert params.sigma > 0

    def test_theta_reasonable(self, sample_prices):
        params = estimate_mean_reversion_params(sample_prices)
        assert params.theta > 0

    def test_raises_on_short_series(self):
        with pytest.raises(ValueError, match="at least"):
            estimate_mean_reversion_params(np.array([100.0, 101.0, 99.0]))

    def test_r_squared_in_range(self, sample_prices):
        params = estimate_mean_reversion_params(sample_prices)
        assert 0.0 <= params.r_squared <= 1.0


class TestComputeHistoricalVolatility:
    def test_returns_positive_float(self, sample_prices):
        vol = compute_historical_volatility(sample_prices)
        assert vol > 0

    def test_annualized_greater_than_daily(self, sample_prices):
        daily = compute_historical_volatility(sample_prices, annualize=False)
        annualized = compute_historical_volatility(sample_prices, annualize=True)
        assert annualized > daily

    def test_known_constant_prices_zero_vol(self):
        prices = np.full(100, 100.0)
        vol = compute_historical_volatility(prices, annualize=False)
        assert vol == 0.0


class TestCalibrateVasicek:
    def test_log_price_calibration(self, sample_prices):
        params = calibrate_vasicek(sample_prices, log_prices=True)
        assert isinstance(params, VasicekParams)
        assert params.k > 0
        assert params.sigma > 0

    def test_linear_calibration(self, sample_prices):
        params = calibrate_vasicek(sample_prices, log_prices=False)
        assert isinstance(params, VasicekParams)
