import pytest

from features.backtesting.strategies.registry import validate_params


def test_validate_sma_params_requires_fast_slower_than_slow():
    with pytest.raises(ValueError, match="fast_period"):
        validate_params("sma_crossover", {"fast_period": 50, "slow_period": 20})


def test_validate_rsi_params_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="oversold"):
        validate_params("rsi_reversion", {"period": 14, "oversold": 80, "overbought": 70})


def test_validate_unknown_strategy():
    with pytest.raises(ValueError, match="Unknown strategy"):
        validate_params("unknown", {})


def test_validate_donchian_params():
    params = validate_params("donchian_breakout", {"channel_period": 30})
    assert params["channel_period"] == 30


def test_validate_bollinger_params():
    params = validate_params("bollinger_breakout", {"period": 20, "std_dev": 2.5})
    assert params["std_dev"] == 2.5


def test_validate_stochastic_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="oversold"):
        validate_params(
            "stochastic_reversion",
            {"k_period": 14, "d_period": 3, "oversold": 80, "overbought": 70},
        )


def test_validate_mfi_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="oversold"):
        validate_params("mfi_reversion", {"period": 14, "oversold": 80, "overbought": 70})


def test_validate_ts_momentum_params():
    params = validate_params("ts_momentum", {"lookback": 126})
    assert params["lookback"] == 126
