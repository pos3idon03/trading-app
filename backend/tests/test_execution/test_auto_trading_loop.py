"""Tests for the auto-trading evaluation loop."""
import math
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.execution.auto_trading_loop import (
    _execute_for_asset,
    build_criteria_signals,
    combine_signals,
    evaluate_asset,
    evaluate_criterion,
    run_auto_trading_cycle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar(close: float = 100.0):
    return SimpleNamespace(
        open=close - 0.5, high=close + 1.0, low=close - 1.0,
        close=close, volume=1000,
    )


def _make_bars(n: int) -> list:
    return [
        _make_bar(close=100.0 + 5.0 * math.sin(i * 0.3) + i * 0.05)
        for i in range(n)
    ]


def _make_asset(**overrides) -> dict:
    base = {
        "strategy_id": 1,
        "asset_id": 10,
        "symbol": "AAPL",
        "mc_prob_positive": 0.6,
        "mc_buy_prob_positive": 0.5,
        "mc_sell_prob_positive": 0.3,
        "ai_conviction": 0.7,
        "ai_buy_conviction": 0.4,
        "ai_sell_conviction": None,
        "ai_sentiment": 0.5,
        "ai_buy_sentiment": 0.4,
        "ai_sell_sentiment": None,
        "ai_macro": 0.65,
        "ai_buy_macro": 0.4,
        "ai_sell_macro": None,
        "combination_mode": "majority",
        "algo_timeframe": "1d",
        "auto_trading_started": True,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# evaluate_criterion
# ---------------------------------------------------------------------------

class TestEvaluateCriterion:
    def test_buy_when_value_above_buy_threshold(self):
        assert evaluate_criterion(0.6, 0.5, 0.3) == "BUY"

    def test_sell_when_value_below_sell_threshold(self):
        assert evaluate_criterion(0.2, 0.5, 0.3) == "SELL"

    def test_neutral_when_between_thresholds(self):
        assert evaluate_criterion(0.4, 0.5, 0.3) == "NEUTRAL"

    def test_neutral_when_value_is_none(self):
        assert evaluate_criterion(None, 0.5, 0.3) == "NEUTRAL"

    def test_neutral_when_no_thresholds(self):
        assert evaluate_criterion(0.6, None, None) == "NEUTRAL"

    def test_buy_when_equal_to_threshold(self):
        assert evaluate_criterion(0.5, 0.5, 0.3) == "BUY"

    def test_sell_when_equal_to_sell_threshold(self):
        assert evaluate_criterion(0.3, 0.5, 0.3) == "SELL"


# ---------------------------------------------------------------------------
# build_criteria_signals
# ---------------------------------------------------------------------------

class TestBuildCriteriaSignals:
    def test_all_buy_when_values_exceed_thresholds(self):
        asset = _make_asset()
        signals = build_criteria_signals(asset)
        assert len(signals) == 4
        assert all(s == "BUY" for s in signals)

    def test_neutral_when_no_thresholds_set(self):
        asset = _make_asset(
            mc_buy_prob_positive=None, mc_sell_prob_positive=None,
            ai_buy_conviction=None, ai_sell_conviction=None,
            ai_buy_sentiment=None, ai_sell_sentiment=None,
            ai_buy_macro=None, ai_sell_macro=None,
        )
        signals = build_criteria_signals(asset)
        assert all(s == "NEUTRAL" for s in signals)

    def test_mixed_signals(self):
        asset = _make_asset(mc_prob_positive=0.2, mc_sell_prob_positive=0.3)
        signals = build_criteria_signals(asset)
        assert signals[0] == "SELL"
        assert signals[1] == "BUY"


# ---------------------------------------------------------------------------
# combine_signals
# ---------------------------------------------------------------------------

class TestCombineSignals:
    def test_all_mode_requires_unanimous(self):
        assert combine_signals(["BUY", "BUY", "BUY"], "all") == "BUY"
        assert combine_signals(["BUY", "BUY", "NEUTRAL"], "all") == "NEUTRAL"
        assert combine_signals(["SELL", "SELL", "SELL"], "all") == "SELL"

    def test_majority_mode(self):
        assert combine_signals(["BUY", "BUY", "NEUTRAL"], "majority") == "BUY"
        assert combine_signals(["SELL", "SELL", "BUY"], "majority") == "SELL"
        assert combine_signals(["BUY", "SELL", "NEUTRAL"], "majority") == "NEUTRAL"

    def test_any_mode(self):
        assert combine_signals(["BUY", "NEUTRAL", "NEUTRAL"], "any") == "BUY"
        assert combine_signals(["NEUTRAL", "SELL", "NEUTRAL"], "any") == "SELL"
        assert combine_signals(["NEUTRAL", "NEUTRAL", "NEUTRAL"], "any") == "NEUTRAL"

    def test_empty_list(self):
        assert combine_signals([], "majority") == "NEUTRAL"

    def test_all_neutral(self):
        assert combine_signals(["NEUTRAL", "NEUTRAL"], "any") == "NEUTRAL"


# ---------------------------------------------------------------------------
# evaluate_asset
# ---------------------------------------------------------------------------

class TestEvaluateAsset:
    @pytest.mark.asyncio
    async def test_returns_buy_when_criteria_met(self):
        asset = _make_asset(combination_mode="majority")
        session = AsyncMock()
        with patch(
            "features.execution.auto_trading_loop._get_algo_signals",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await evaluate_asset(session, asset)
        assert result == "BUY"

    @pytest.mark.asyncio
    async def test_returns_neutral_when_no_thresholds(self):
        asset = _make_asset(
            mc_buy_prob_positive=None, mc_sell_prob_positive=None,
            ai_buy_conviction=None, ai_sell_conviction=None,
            ai_buy_sentiment=None, ai_sell_sentiment=None,
            ai_buy_macro=None, ai_sell_macro=None,
            combination_mode="majority",
        )
        session = AsyncMock()
        with patch(
            "features.execution.auto_trading_loop._get_algo_signals",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await evaluate_asset(session, asset)
        assert result == "NEUTRAL"

    @pytest.mark.asyncio
    async def test_includes_algo_signals_in_evaluation(self):
        asset = _make_asset(
            combination_mode="majority",
            mc_prob_positive=0.4, mc_buy_prob_positive=0.5,
            ai_conviction=0.3, ai_buy_conviction=0.5,
            ai_sentiment=0.3, ai_buy_sentiment=0.5,
            ai_macro=0.3, ai_buy_macro=0.5,
        )
        session = AsyncMock()
        with patch(
            "features.execution.auto_trading_loop._get_algo_signals",
            new_callable=AsyncMock, return_value=["BUY", "BUY", "BUY", "BUY", "BUY"],
        ):
            result = await evaluate_asset(session, asset)
        assert result == "BUY"


# ---------------------------------------------------------------------------
# run_auto_trading_cycle
# ---------------------------------------------------------------------------

class TestRunAutoTradingCycle:
    @pytest.mark.asyncio
    async def test_skips_when_kill_switch_active(self):
        session = AsyncMock()
        with patch("features.execution.auto_trading_loop.get_risk_manager") as mock_rm:
            mock_rm.return_value.config.kill_switch_active = True
            results = await run_auto_trading_cycle(session)
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_running_assets(self):
        session = AsyncMock()
        with patch("features.execution.auto_trading_loop.get_risk_manager") as mock_rm, \
             patch("features.execution.auto_trading_loop.list_auto_trading_assets",
                   new_callable=AsyncMock, return_value=[]):
            mock_rm.return_value.config.kill_switch_active = False
            results = await run_auto_trading_cycle(session)
        assert results == []

    @pytest.mark.asyncio
    async def test_evaluates_running_assets(self):
        asset = _make_asset()
        bars = _make_bars(60)
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.get_risk_manager") as mock_rm, \
             patch("features.execution.auto_trading_loop.list_auto_trading_assets",
                   new_callable=AsyncMock, return_value=[asset]), \
             patch("features.execution.auto_trading_loop.evaluate_asset",
                   new_callable=AsyncMock, return_value="BUY"), \
             patch("features.execution.auto_trading_loop._get_bars_for_asset",
                   new_callable=AsyncMock, return_value=bars), \
             patch("features.execution.auto_trading_loop._execute_for_asset",
                   new_callable=AsyncMock) as mock_exec:
            mock_rm.return_value.config.kill_switch_active = False
            results = await run_auto_trading_cycle(session)

        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["signal"] == "BUY"
        assert results[0]["executed"] is True
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_execute_on_neutral(self):
        asset = _make_asset()
        bars = _make_bars(60)
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.get_risk_manager") as mock_rm, \
             patch("features.execution.auto_trading_loop.list_auto_trading_assets",
                   new_callable=AsyncMock, return_value=[asset]), \
             patch("features.execution.auto_trading_loop.evaluate_asset",
                   new_callable=AsyncMock, return_value="NEUTRAL"), \
             patch("features.execution.auto_trading_loop._get_bars_for_asset",
                   new_callable=AsyncMock, return_value=bars), \
             patch("features.execution.auto_trading_loop._execute_for_asset",
                   new_callable=AsyncMock) as mock_exec:
            mock_rm.return_value.config.kill_switch_active = False
            results = await run_auto_trading_cycle(session)

        assert len(results) == 1
        assert results[0]["signal"] == "NEUTRAL"
        assert results[0]["executed"] is False
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_asset_error_gracefully(self):
        asset = _make_asset()
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.get_risk_manager") as mock_rm, \
             patch("features.execution.auto_trading_loop.list_auto_trading_assets",
                   new_callable=AsyncMock, return_value=[asset]), \
             patch("features.execution.auto_trading_loop.evaluate_asset",
                   new_callable=AsyncMock, side_effect=RuntimeError("network error")):
            mock_rm.return_value.config.kill_switch_active = False
            results = await run_auto_trading_cycle(session)

        assert len(results) == 1
        assert results[0]["signal"] == "ERROR"
        assert "network error" in results[0]["error"]

    @pytest.mark.asyncio
    async def test_skips_non_started_assets(self):
        asset = _make_asset(auto_trading_started=False)
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.get_risk_manager") as mock_rm, \
             patch("features.execution.auto_trading_loop.list_auto_trading_assets",
                   new_callable=AsyncMock, return_value=[asset]):
            mock_rm.return_value.config.kill_switch_active = False
            results = await run_auto_trading_cycle(session)

        assert results == []


# ---------------------------------------------------------------------------
# _execute_for_asset – symbol resolver integration
# ---------------------------------------------------------------------------

class TestExecuteForAssetPositionGuard:
    """_execute_for_asset must skip when position state doesn't match signal."""

    @pytest.mark.asyncio
    async def test_buy_skips_when_already_holding(self):
        asset = _make_asset(symbol="BTC-USD", asset_type="crypto")
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.has_position", return_value=True), \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock) as mock_create:
            await _execute_for_asset(session, asset, "BUY", 60000.0)

        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_sell_skips_when_not_holding(self):
        asset = _make_asset(symbol="BTC-USD", asset_type="crypto")
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.has_position", return_value=False), \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock) as mock_create:
            await _execute_for_asset(session, asset, "SELL", 60000.0)

        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_buy_proceeds_when_not_holding(self):
        asset = _make_asset(symbol="BTC-USD", asset_type="crypto")
        session = AsyncMock()

        mock_plan = MagicMock()
        mock_plan.symbol = "BTC/USD"
        mock_plan.side = "buy"
        mock_plan.qty = 0.001
        mock_plan.order_type = "market"

        mock_result = MagicMock()
        mock_result.status = "filled"
        mock_result.order_id = "abc"
        mock_result.filled_price = 60000.0
        mock_result.filled_qty = 0.001

        with patch("features.execution.auto_trading_loop.has_position", return_value=False), \
             patch("features.execution.auto_trading_loop.plan_order_from_signal",
                   return_value=mock_plan), \
             patch("features.execution.auto_trading_loop.sync_portfolio",
                   return_value=MagicMock()), \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock, return_value=1) as mock_create, \
             patch("features.execution.auto_trading_loop.execute_order_plan",
                   return_value=(MagicMock(violations=[]), mock_result)), \
             patch("features.execution.auto_trading_loop.update_order_status",
                   new_callable=AsyncMock):
            await _execute_for_asset(session, asset, "BUY", 60000.0)

        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sell_proceeds_when_holding(self):
        asset = _make_asset(symbol="BTC-USD", asset_type="crypto")
        session = AsyncMock()

        mock_plan = MagicMock()
        mock_plan.symbol = "BTC/USD"
        mock_plan.side = "sell"
        mock_plan.qty = 0.05
        mock_plan.order_type = "market"

        mock_result = MagicMock()
        mock_result.status = "filled"
        mock_result.order_id = "xyz"
        mock_result.filled_price = 58000.0
        mock_result.filled_qty = 0.05

        with patch("features.execution.auto_trading_loop.has_position", return_value=True), \
             patch("features.execution.auto_trading_loop.plan_order_from_signal",
                   return_value=mock_plan), \
             patch("features.execution.auto_trading_loop.sync_portfolio",
                   return_value=MagicMock()), \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock, return_value=2) as mock_create, \
             patch("features.execution.auto_trading_loop.execute_order_plan",
                   return_value=(MagicMock(violations=[]), mock_result)), \
             patch("features.execution.auto_trading_loop.update_order_status",
                   new_callable=AsyncMock):
            await _execute_for_asset(session, asset, "SELL", 58000.0)

        mock_create.assert_called_once()


class TestExecuteForAssetSymbolResolution:
    @pytest.mark.asyncio
    async def test_skips_non_us_equity(self):
        """BARC.L is not supported on Alpaca – no order should be placed."""
        asset = _make_asset(symbol="BARC.L", asset_type="stock")
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock) as mock_create, \
             patch("features.execution.auto_trading_loop.execute_order_plan") as mock_exec:
            await _execute_for_asset(session, asset, "BUY", 150.0)

        mock_create.assert_not_called()
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_forex_symbol(self):
        """Forex symbols are unsupported on Alpaca."""
        asset = _make_asset(symbol="EURUSD=X", asset_type="forex")
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock) as mock_create, \
             patch("features.execution.auto_trading_loop.execute_order_plan") as mock_exec:
            await _execute_for_asset(session, asset, "BUY", 1.1)

        mock_create.assert_not_called()
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_normalized_alpaca_symbol_for_crypto(self):
        """BTC-USD stored in DB as yfinance key; broker receives BTC/USD."""
        asset = _make_asset(symbol="BTC-USD", asset_type="crypto")
        session = AsyncMock()

        mock_plan = MagicMock()
        mock_plan.symbol = "BTC/USD"
        mock_plan.side = "buy"
        mock_plan.qty = 0.001
        mock_plan.order_type = "market"

        mock_result = MagicMock()
        mock_result.status = "filled"
        mock_result.order_id = "abc123"
        mock_result.filled_price = 60000.0
        mock_result.filled_qty = 0.001

        with patch("features.execution.auto_trading_loop.has_position", return_value=False), \
             patch("features.execution.auto_trading_loop.plan_order_from_signal",
                   return_value=mock_plan), \
             patch("features.execution.auto_trading_loop.sync_portfolio",
                   return_value=MagicMock()), \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock, return_value=42) as mock_create, \
             patch("features.execution.auto_trading_loop.execute_order_plan",
                   return_value=(MagicMock(violations=[]), mock_result)), \
             patch("features.execution.auto_trading_loop.update_order_status",
                   new_callable=AsyncMock):
            await _execute_for_asset(session, asset, "BUY", 60000.0)

        # Order stored with yfinance symbol (matches asset queries by frontend)
        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("symbol") == "BTC-USD"

    @pytest.mark.asyncio
    async def test_us_equity_symbol_unchanged(self):
        """US equity symbols like AAPL pass through unchanged."""
        asset = _make_asset(symbol="AAPL", asset_type="stock")
        session = AsyncMock()

        mock_plan = MagicMock()
        mock_plan.symbol = "AAPL"
        mock_plan.side = "buy"
        mock_plan.qty = 1
        mock_plan.order_type = "market"

        mock_result = MagicMock()
        mock_result.status = "filled"
        mock_result.order_id = "xyz789"
        mock_result.filled_price = 180.0
        mock_result.filled_qty = 1

        with patch("features.execution.auto_trading_loop.has_position", return_value=False), \
             patch("features.execution.auto_trading_loop.plan_order_from_signal",
                   return_value=mock_plan), \
             patch("features.execution.auto_trading_loop.sync_portfolio",
                   return_value=MagicMock()), \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock, return_value=99) as mock_create, \
             patch("features.execution.auto_trading_loop.execute_order_plan",
                   return_value=(MagicMock(violations=[]), mock_result)), \
             patch("features.execution.auto_trading_loop.update_order_status",
                   new_callable=AsyncMock):
            await _execute_for_asset(session, asset, "BUY", 180.0)

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("symbol") == "AAPL"

    @pytest.mark.asyncio
    async def test_neutral_signal_does_not_reach_symbol_resolver(self):
        """NEUTRAL signal exits early before any symbol resolution."""
        asset = _make_asset(symbol="BTC-USD", asset_type="crypto")
        session = AsyncMock()

        with patch("features.execution.auto_trading_loop.to_alpaca_symbol") as mock_resolver, \
             patch("features.execution.auto_trading_loop.create_order",
                   new_callable=AsyncMock):
            await _execute_for_asset(session, asset, "NEUTRAL", 60000.0)

        mock_resolver.assert_not_called()
