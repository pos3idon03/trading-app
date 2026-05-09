"""Tests for performance metric calculation functions."""
import numpy as np
import pandas as pd
import pytest

from features.backtesting.metrics import (
    calculate_annualized_return,
    calculate_max_drawdown,
    calculate_profit_factor,
    calculate_sharpe,
    calculate_sortino,
    calculate_win_rate,
    compile_all_metrics,
)


@pytest.fixture
def positive_returns():
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.001, 0.01, 252))


@pytest.fixture
def equity_series():
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.01, 252)
    return pd.Series(100_000 * np.cumprod(1 + returns))


@pytest.fixture
def sample_trades():
    return [
        {"pnl": 500},
        {"pnl": -200},
        {"pnl": 300},
        {"pnl": -100},
        {"pnl": 800},
    ]


class TestCalculateSharpe:
    def test_returns_float(self, positive_returns):
        sharpe = calculate_sharpe(positive_returns)
        assert isinstance(sharpe, float)

    def test_positive_for_positive_returns(self, positive_returns):
        assert calculate_sharpe(positive_returns) > 0

    def test_zero_std_returns_zero(self):
        returns = pd.Series([0.0] * 100)
        assert calculate_sharpe(returns) == 0.0


class TestCalculateSortino:
    def test_returns_float(self, positive_returns):
        sortino = calculate_sortino(positive_returns)
        assert isinstance(sortino, float)

    def test_sortino_gte_sharpe_for_mostly_positive(self, positive_returns):
        sharpe = calculate_sharpe(positive_returns)
        sortino = calculate_sortino(positive_returns)
        assert sortino >= sharpe - 1.0


class TestCalculateMaxDrawdown:
    def test_returns_negative_or_zero(self, equity_series):
        mdd = calculate_max_drawdown(equity_series)
        assert mdd <= 0

    def test_monotonic_increasing_no_drawdown(self):
        equity = pd.Series(np.linspace(100, 200, 100))
        assert calculate_max_drawdown(equity) == 0.0

    def test_known_drawdown(self):
        equity = pd.Series([100, 110, 90, 95, 105])
        mdd = calculate_max_drawdown(equity)
        assert mdd < 0
        expected = (90 - 110) / 110
        assert abs(mdd - expected) < 0.001

    def test_empty_series_returns_zero(self):
        assert calculate_max_drawdown(pd.Series([])) == 0.0


class TestCalculateWinRate:
    def test_all_profitable(self):
        trades = [{"pnl": 100}, {"pnl": 200}, {"pnl": 50}]
        assert calculate_win_rate(trades) == 1.0

    def test_all_losses(self):
        trades = [{"pnl": -100}, {"pnl": -50}]
        assert calculate_win_rate(trades) == 0.0

    def test_mixed_trades(self, sample_trades):
        wr = calculate_win_rate(sample_trades)
        assert 0.0 < wr < 1.0

    def test_empty_trades_returns_zero(self):
        assert calculate_win_rate([]) == 0.0


class TestCalculateProfitFactor:
    def test_profitable_strategy(self):
        trades = [{"pnl": 500}, {"pnl": 300}, {"pnl": -100}]
        pf = calculate_profit_factor(trades)
        assert pf > 1.0

    def test_losing_strategy(self):
        trades = [{"pnl": 100}, {"pnl": -500}, {"pnl": -300}]
        pf = calculate_profit_factor(trades)
        assert pf < 1.0

    def test_no_losses_returns_zero(self):
        """When there are no losing trades gross_loss is 0; result is 0.0 (JSON-safe)."""
        trades = [{"pnl": 100}, {"pnl": 200}]
        assert calculate_profit_factor(trades) == 0.0


class TestCompileAllMetrics:
    def test_returns_all_keys(self, positive_returns, equity_series, sample_trades):
        metrics = compile_all_metrics(positive_returns, equity_series, sample_trades)
        expected_keys = [
            "sharpe_ratio", "sortino_ratio", "max_drawdown",
            "win_rate", "profit_factor", "total_return",
            "annualized_return", "num_trades",
        ]
        for key in expected_keys:
            assert key in metrics

    def test_num_trades_matches_input(self, positive_returns, equity_series, sample_trades):
        metrics = compile_all_metrics(positive_returns, equity_series, sample_trades)
        assert metrics["num_trades"] == len(sample_trades)
