"""Tests for Vasicek model parameter estimation."""
import numpy as np
import pytest

from features.quantitative_engine.vasicek import (
    VasicekParams,
    calibrate_vasicek,
    compute_historical_volatility,
    estimate_drift_rate,
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


class TestEstimateDriftRate:
    def test_positive_drift_for_trending_prices(self):
        """Monotonically increasing prices should yield a positive mu."""
        prices = np.array([100.0 * (1.01 ** i) for i in range(50)])
        mu = estimate_drift_rate(prices, dt=1 / 252)
        assert mu > 0

    def test_negative_drift_for_declining_prices(self):
        """Monotonically decreasing prices should yield a negative mu."""
        prices = np.array([100.0 * (0.99 ** i) for i in range(50)])
        mu = estimate_drift_rate(prices, dt=1 / 252)
        assert mu < 0

    def test_zero_drift_for_flat_prices(self):
        """Constant prices should yield mu close to zero."""
        prices = np.full(50, 100.0)
        mu = estimate_drift_rate(prices, dt=1 / 252)
        assert abs(mu) < 1e-10

    def test_returns_float(self):
        prices = np.linspace(100, 200, 50)
        result = estimate_drift_rate(prices, dt=1 / 252)
        assert isinstance(result, float)

    def test_short_series_returns_zero(self):
        """Less than 2 valid prices should return 0.0 without error."""
        assert estimate_drift_rate(np.array([100.0]), dt=1 / 252) == 0.0


class TestCalibrateVasicek:
    def test_log_price_calibration(self, sample_prices):
        params = calibrate_vasicek(sample_prices, log_prices=True)
        assert isinstance(params, VasicekParams)
        assert params.k > 0
        assert params.sigma > 0

    def test_linear_calibration(self, sample_prices):
        params = calibrate_vasicek(sample_prices, log_prices=False)
        assert isinstance(params, VasicekParams)

    def test_mu_is_populated_after_calibration(self, sample_prices):
        """calibrate_vasicek must return a nonzero mu for a trending price series."""
        trending = np.array([100.0 * (1.001 ** i) for i in range(60)])
        params = calibrate_vasicek(trending, dt=1 / 252)
        assert params.mu != 0.0

    def test_estimate_mean_reversion_params_sets_mu(self, sample_prices):
        """estimate_mean_reversion_params must populate mu on the returned dataclass."""
        params = estimate_mean_reversion_params(sample_prices)
        assert hasattr(params, "mu")
        assert isinstance(params.mu, float)
