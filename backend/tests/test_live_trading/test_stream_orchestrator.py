"""Tests for stream orchestrator auto-start logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.live_trading.resampler import ResamplingEngine
from features.live_trading.stream_orchestrator import (
    StreamConfig,
    collect_running_stream_config,
    ensure_resampler_timeframes,
    sync_stream_with_running_assets,
)


class TestCollectRunningStreamConfig:
    @pytest.mark.asyncio
    async def test_returns_symbols_and_timeframes_from_running_assets(self):
        session = AsyncMock()
        rows = [
            {"symbol": "AAPL", "auto_trading_started": True, "algo_timeframe": "5m"},
            {"symbol": "BTC/USD", "auto_trading_started": True, "algo_timeframe": "1h"},
            {"symbol": "MSFT", "auto_trading_started": False, "algo_timeframe": "1d"},
        ]
        with patch(
            "features.live_trading.stream_orchestrator.list_auto_trading_assets",
            new=AsyncMock(return_value=rows),
        ):
            config = await collect_running_stream_config(session)

        assert config == StreamConfig(symbols=["AAPL", "BTC/USD"], timeframes=["1h", "5m"])

    @pytest.mark.asyncio
    async def test_empty_when_nothing_running(self):
        session = AsyncMock()
        rows = [{"symbol": "AAPL", "auto_trading_started": False, "algo_timeframe": "5m"}]
        with patch(
            "features.live_trading.stream_orchestrator.list_auto_trading_assets",
            new=AsyncMock(return_value=rows),
        ):
            config = await collect_running_stream_config(session)

        assert config.symbols == []
        assert config.timeframes == []


class TestEnsureResamplerTimeframes:
    def test_updates_resampler_and_persistence(self):
        resampler = ResamplingEngine(timeframes=["1d"])
        with patch(
            "features.live_trading.stream_orchestrator.set_persist_timeframes",
        ) as mock_persist:
            ensure_resampler_timeframes(["5m", "1h"], resampler)

        assert resampler.active_timeframes == ["5m", "1h"]
        mock_persist.assert_called_once_with(["5m", "1h"])


class TestSyncStreamWithRunningAssets:
    @pytest.mark.asyncio
    async def test_stops_stream_when_no_running_assets(self):
        session = AsyncMock()
        resampler = ResamplingEngine()
        mock_stream = MagicMock()
        mock_stream.stop = AsyncMock()

        with patch(
            "features.live_trading.stream_orchestrator.collect_running_stream_config",
            new=AsyncMock(return_value=StreamConfig(symbols=[], timeframes=[])),
        ), patch(
            "features.live_trading.stream_orchestrator.ensure_resampler_timeframes",
        ), patch(
            "features.live_trading.stream_orchestrator.get_stream",
            return_value=mock_stream,
        ):
            config = await sync_stream_with_running_assets(session, resampler)

        assert config.symbols == []
        mock_stream.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reconciles_stream_for_running_assets(self):
        session = AsyncMock()
        resampler = ResamplingEngine()
        plan = MagicMock()
        plan.app_symbols = ["AAPL"]
        plan.entries = [MagicMock()]

        mock_stream = MagicMock()
        mock_stream.status.connected = True
        mock_stream.status.reconnecting = False
        mock_stream.reconcile = AsyncMock(return_value="restarted")

        with patch(
            "features.live_trading.stream_orchestrator.collect_running_stream_config",
            new=AsyncMock(return_value=StreamConfig(symbols=["AAPL"], timeframes=["5m"])),
        ), patch(
            "features.live_trading.stream_orchestrator.ensure_resampler_timeframes",
        ), patch(
            "features.live_trading.stream_orchestrator.ensure_historical_warmup",
            new=AsyncMock(),
        ), patch(
            "features.live_trading.stream_orchestrator.build_stream_plan",
            new=AsyncMock(return_value=plan),
        ), patch(
            "features.live_trading.stream_orchestrator._register_streaming_assets",
            new=AsyncMock(),
        ), patch(
            "features.live_trading.stream_orchestrator.attach_stream_handlers",
        ), patch(
            "features.live_trading.stream_orchestrator.get_stream",
            return_value=mock_stream,
        ):
            config = await sync_stream_with_running_assets(session, resampler)

        assert config.symbols == ["AAPL"]
        mock_stream.reconcile.assert_awaited_once_with(plan)

    @pytest.mark.asyncio
    async def test_second_sync_uses_reconcile_noop_when_healthy(self):
        session = AsyncMock()
        resampler = ResamplingEngine()
        plan = MagicMock()
        plan.app_symbols = ["AAPL"]
        plan.entries = [MagicMock()]

        mock_stream = MagicMock()
        mock_stream.status.connected = True
        mock_stream.status.reconnecting = False
        mock_stream.reconcile = AsyncMock(return_value="noop")

        patches = [
            patch(
                "features.live_trading.stream_orchestrator.collect_running_stream_config",
                new=AsyncMock(
                    return_value=StreamConfig(symbols=["AAPL"], timeframes=["5m"]),
                ),
            ),
            patch("features.live_trading.stream_orchestrator.ensure_resampler_timeframes"),
            patch(
                "features.live_trading.stream_orchestrator.ensure_historical_warmup",
                new=AsyncMock(),
            ),
            patch(
                "features.live_trading.stream_orchestrator.build_stream_plan",
                new=AsyncMock(return_value=plan),
            ),
            patch(
                "features.live_trading.stream_orchestrator._register_streaming_assets",
                new=AsyncMock(),
            ),
            patch("features.live_trading.stream_orchestrator.attach_stream_handlers"),
            patch(
                "features.live_trading.stream_orchestrator.get_stream",
                return_value=mock_stream,
            ),
        ]

        for p in patches:
            p.start()
        try:
            await sync_stream_with_running_assets(session, resampler)
            await sync_stream_with_running_assets(session, resampler)
        finally:
            for p in patches:
                p.stop()

        assert mock_stream.reconcile.await_count == 2
        mock_stream.stop.assert_not_called()
