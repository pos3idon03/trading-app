"""Tests for walk-forward MC backtest engine and route."""
from datetime import datetime, timezone
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from features.quantitative_engine.mc_backtest import (
    MAX_EVAL_BARS,
    McBacktestConfig,
    StepProbResult,
    _append_open_trade_row,
    _smooth_probs,
    compute_prob_distribution_stats,
    compute_prob_zone_stats,
    evaluate_mc_signal,
    run_mc_backtest,
    simulate_portfolio,
)


def _make_price_df(n: int = 120, start: datetime | None = None) -> pd.DataFrame:
    start = start or datetime(2020, 1, 1, tzinfo=timezone.utc)
    times = pd.date_range(start, periods=n, freq="D", tz=timezone.utc)
    prices = 100 + np.cumsum(np.random.default_rng(42).normal(0, 0.5, n))
    return pd.DataFrame({
        "time": times,
        "open": prices,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": 1000.0,
    })


class TestEvaluateMcSignal:
    def test_flat_buy_when_above_buy_threshold(self):
        assert evaluate_mc_signal(0.7, False, 0.65, 0.4) == "BUY"

    def test_flat_stays_flat_below_buy(self):
        assert evaluate_mc_signal(0.6, False, 0.65, 0.4) == "FLAT"

    def test_long_sells_below_sell(self):
        assert evaluate_mc_signal(0.35, True, 0.65, 0.4) == "SELL"

    def test_long_stays_flat_in_mid_band(self):
        assert evaluate_mc_signal(0.55, True, 0.65, 0.4) == "FLAT"

    def test_long_stays_flat_between_sell_and_buy(self):
        assert evaluate_mc_signal(0.45, True, 0.65, 0.4) == "FLAT"

    def test_long_stays_flat_at_or_above_buy(self):
        assert evaluate_mc_signal(0.70, True, 0.65, 0.4) == "FLAT"


class TestProbZoneStats:
    def test_zone_percentages(self):
        log = [
            {"prob_positive": 0.7},
            {"prob_positive": 0.5},
            {"prob_positive": 0.35},
        ]
        stats = compute_prob_zone_stats(log, buy_threshold=0.65, sell_threshold=0.40)
        assert stats["entry_zone_pct"] == pytest.approx(33.3, abs=0.1)
        assert stats["middle_zone_pct"] == pytest.approx(33.3, abs=0.1)
        assert stats["exit_zone_pct"] == pytest.approx(33.3, abs=0.1)
        assert stats["bars_with_prob"] == 3


class TestProbDistributionStats:
    def _log(self, probs: list[float], effective: bool = False) -> list[dict]:
        entries = []
        for p in probs:
            row = {"prob_positive": p, "signal": "FLAT"}
            if effective:
                row["effective_prob"] = p
            entries.append(row)
        return entries

    def test_percentiles_and_suggestions(self):
        probs = [0.40 + i * 0.02 for i in range(12)]
        stats = compute_prob_distribution_stats(self._log(probs))
        assert stats["prob_min"] == pytest.approx(0.40, abs=0.001)
        assert stats["prob_max"] == pytest.approx(0.62, abs=0.001)
        assert stats["suggested_buy_threshold"] == pytest.approx(0.57, abs=0.02)
        assert stats["suggested_sell_threshold"] == pytest.approx(0.45, abs=0.02)
        assert stats["suggested_sell_threshold"] < stats["suggested_buy_threshold"]

    def test_narrow_band_expands_min_gap(self):
        stats = compute_prob_distribution_stats(self._log([0.50] * 10))
        assert stats["suggested_buy_threshold"] is not None
        assert stats["suggested_sell_threshold"] is not None
        gap = stats["suggested_buy_threshold"] - stats["suggested_sell_threshold"]
        assert gap >= 0.03

    def test_insufficient_bars_omits_suggestions(self):
        stats = compute_prob_distribution_stats(self._log([0.45, 0.55, 0.50]))
        assert stats["prob_median"] == pytest.approx(0.50, abs=0.01)
        assert stats["suggested_buy_threshold"] is None
        assert stats["suggested_sell_threshold"] is None

    def test_prefers_effective_prob(self):
        log = [
            {"prob_positive": 0.90, "effective_prob": 0.46, "signal": "FLAT"},
            {"prob_positive": 0.90, "effective_prob": 0.54, "signal": "FLAT"},
        ] * 6
        stats = compute_prob_distribution_stats(log)
        assert stats["prob_min"] == pytest.approx(0.46, abs=0.001)
        assert stats["prob_max"] == pytest.approx(0.54, abs=0.001)


class TestSmoothProbs:
    def test_moving_average(self):
        raw = [StepProbResult(0.4), StepProbResult(0.6), StepProbResult(0.8)]
        assert _smooth_probs(raw, 2) == pytest.approx([0.4, 0.5, 0.7])


class TestSimulatePortfolio:
    def test_buy_then_sell_produces_one_closed_trade(self):
        eval_df = _make_price_df(5)
        actions = ["BUY", "FLAT", "FLAT", "SELL", "FLAT"]
        equity, closed, exec_log, _, open_trade, shares = simulate_portfolio(
            eval_df, actions, 1000.0,
        )
        assert len(equity) == 5
        assert len(closed) == 1
        assert closed[0]["pnl"] is not None
        assert len(exec_log) == 2
        assert exec_log[0]["side"] == "buy"
        assert exec_log[1]["side"] == "sell"
        assert open_trade is None
        assert shares == 0.0

    def test_buy_without_sell_records_execution_and_open_row(self):
        eval_df = _make_price_df(4)
        actions = ["BUY", "FLAT", "FLAT", "FLAT"]
        _, closed, exec_log, _, open_trade, shares = simulate_portfolio(
            eval_df, actions, 1000.0,
        )
        assert len(closed) == 0
        assert len(exec_log) == 1
        assert exec_log[0]["side"] == "buy"
        assert open_trade is not None
        assert shares > 0

        display = _append_open_trade_row(
            closed, open_trade, shares, float(eval_df["close"].iloc[-1]),
        )
        assert len(display) == 1
        assert display[0]["status"] == "open"

    def test_all_flat_keeps_initial_capital(self):
        eval_df = _make_price_df(4)
        actions = ["FLAT"] * 4
        equity, closed, exec_log, series, open_trade, shares = simulate_portfolio(
            eval_df, actions, 1000.0,
        )
        assert len(closed) == 0
        assert len(exec_log) == 0
        assert open_trade is None
        assert series.iloc[-1] == pytest.approx(1000.0, rel=1e-3)


class TestMcBacktestRequestDTO:
    def test_valid_request(self):
        pytest.importorskip("pydantic")
        from dtos.simulation_dto import McBacktestRequest

        req = McBacktestRequest(
            symbol="AAPL",
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        assert req.buy_threshold == 0.65
        assert req.entry_confirmation_bars == 1

    def test_rejects_bad_threshold_order(self):
        pytest.importorskip("pydantic")
        from pydantic import ValidationError
        from dtos.simulation_dto import McBacktestRequest

        with pytest.raises(ValidationError):
            McBacktestRequest(
                symbol="AAPL",
                start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                buy_threshold=0.4,
                sell_threshold=0.6,
            )

    def test_combo_requires_algo_strategies(self):
        pytest.importorskip("pydantic")
        from pydantic import ValidationError
        from dtos.simulation_dto import McBacktestRequest

        with pytest.raises(ValidationError):
            McBacktestRequest(
                symbol="AAPL",
                start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                combo_enabled=True,
                algo_strategies=[],
            )


class TestRunMcBacktest:
    @patch("features.quantitative_engine.mc_backtest.run_single_step_prob")
    def test_walk_forward_produces_metrics(self, mock_prob):
        mock_prob.return_value = StepProbResult(prob=0.55, prob_trend=0.55)
        full_df = _make_price_df(60)
        config = McBacktestConfig(
            timeframe="1d",
            start_date=full_df["time"].iloc[30],
            end_date=full_df["time"].iloc[-1],
            model_type="merton",
            calibration_lookback_days=365,
            num_paths=100,
            buy_threshold=0.65,
            sell_threshold=0.40,
            initial_capital=1000.0,
        )
        result = run_mc_backtest(full_df, config)
        assert result.bars_evaluated == 30
        assert "total_return" in result.metrics
        assert "excess_return" in result.metrics
        assert result.zone_stats["bars_with_prob"] > 0
        assert "prob_p75" in result.zone_stats
        assert "suggested_buy_threshold" in result.zone_stats
        assert len(result.equity_curve) == 30

    @patch("features.quantitative_engine.mc_backtest.run_single_step_prob")
    def test_entry_confirmation_delays_buy(self, mock_prob):
        mock_prob.side_effect = [
            StepProbResult(prob=0.7),
            StepProbResult(prob=0.7),
            StepProbResult(prob=0.35),
            StepProbResult(prob=0.6),
        ] + [StepProbResult(prob=0.5)] * 20
        full_df = _make_price_df(60)
        config = McBacktestConfig(
            timeframe="1d",
            start_date=full_df["time"].iloc[30],
            end_date=full_df["time"].iloc[35],
            model_type="merton",
            calibration_lookback_days=365,
            num_paths=100,
            buy_threshold=0.65,
            sell_threshold=0.40,
            entry_confirmation_bars=2,
        )
        result = run_mc_backtest(full_df, config)
        buy_signals = [s for s in result.signal_log if s["signal"] == "BUY"]
        assert len(buy_signals) <= 1

    @patch("features.quantitative_engine.mc_backtest.run_single_step_prob")
    def test_blended_signal_log_includes_diagnostics(self, mock_prob):
        mock_prob.return_value = StepProbResult(
            prob=0.58,
            prob_trend=0.62,
            prob_reversion=0.48,
            regime_weight=0.5,
        )
        full_df = _make_price_df(60)
        config = McBacktestConfig(
            timeframe="1d",
            start_date=full_df["time"].iloc[30],
            end_date=full_df["time"].iloc[-1],
            model_type="blended",
            calibration_lookback_days=365,
            num_paths=100,
            buy_threshold=0.65,
            sell_threshold=0.40,
        )
        result = run_mc_backtest(full_df, config)
        with_diag = [s for s in result.signal_log if s.get("prob_trend") is not None]
        assert len(with_diag) > 0
        assert with_diag[0]["regime_weight"] == 0.5

    def test_rejects_too_many_bars(self):
        full_df = _make_price_df(MAX_EVAL_BARS + 50)
        config = McBacktestConfig(
            timeframe="1d",
            start_date=full_df["time"].iloc[0],
            end_date=full_df["time"].iloc[-1],
            model_type="merton",
            calibration_lookback_days=365,
            num_paths=100,
            buy_threshold=0.65,
            sell_threshold=0.40,
        )
        with pytest.raises(ValueError, match="maximum"):
            run_mc_backtest(full_df, config)

    @patch("features.quantitative_engine.mc_backtest.run_single_step_prob")
    def test_combo_enabled_produces_combo_signals(self, mock_prob):
        mock_prob.return_value = StepProbResult(prob=0.7)
        full_df = _make_price_df(80)
        from features.quantitative_engine.mc_combo import AlgoComboLeg

        mc_only = run_mc_backtest(
            full_df,
            McBacktestConfig(
                timeframe="1d",
                start_date=full_df["time"].iloc[50],
                end_date=full_df["time"].iloc[55],
                model_type="merton",
                calibration_lookback_days=365,
                num_paths=100,
                buy_threshold=0.65,
                sell_threshold=0.40,
            ),
        )
        combo = run_mc_backtest(
            full_df,
            McBacktestConfig(
                timeframe="1d",
                start_date=full_df["time"].iloc[50],
                end_date=full_df["time"].iloc[55],
                model_type="merton",
                calibration_lookback_days=365,
                num_paths=100,
                buy_threshold=0.65,
                sell_threshold=0.40,
                combo_enabled=True,
                combination_mode="and",
                algo_strategies=[
                    AlgoComboLeg("rsi", {"period": 14}, weight=1.0, timeframe="1d"),
                ],
            ),
        )
        assert combo.combo_signals is not None
        assert len(combo.combo_signals) == 2
        assert combo.combo_signals[0]["strategy_name"] == "mc_prob"
        assert combo.combined_signal_timeline is not None
        assert len(combo.combined_signal_timeline) == combo.bars_evaluated
        mc_buys = sum(1 for s in mc_only.signal_log if s["signal"] == "BUY")
        combo_buys = sum(1 for s in combo.signal_log if s["signal"] == "BUY")
        assert combo_buys <= mc_buys
