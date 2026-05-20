"""Tests for ADX regime weighting."""
import pandas as pd

from features.quantitative_engine.regime_weight import calc_adx, trend_weight_from_adx


class TestTrendWeightFromAdx:
    def test_low_adx_favors_reversion(self):
        assert trend_weight_from_adx(10.0) == 0.0

    def test_high_adx_favors_trend(self):
        assert trend_weight_from_adx(30.0) == 1.0

    def test_mid_adx_interpolates(self):
        w = trend_weight_from_adx(20.0, low=15.0, high=25.0)
        assert w == 0.5

    def test_nan_adx_returns_half(self):
        assert trend_weight_from_adx(float("nan")) == 0.5


class TestCalcAdx:
    def test_returns_series(self):
        n = 50
        close = pd.Series(range(100, 100 + n), dtype=float)
        high = close + 1
        low = close - 1
        adx = calc_adx(high, low, close, period=14)
        assert len(adx) == n
        assert adx.iloc[-1] >= 0
