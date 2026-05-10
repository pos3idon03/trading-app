"""Tests verifying asset_id FK is propagated through DAL create functions."""
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# ai_agent_dal: create_analysis stores asset_id
# ---------------------------------------------------------------------------

class TestCreateAnalysisAssetId:
    @pytest.mark.asyncio
    async def test_stores_asset_id_when_provided(self):
        from dal.ai_agent_dal import create_analysis

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_analysis(mock_session, symbol="AAPL", llm="gpt-4o-mini", asset_id=42)

        assert added_record is not None
        assert added_record.asset_id == 42
        assert added_record.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_asset_id_defaults_to_none(self):
        from dal.ai_agent_dal import create_analysis

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_analysis(mock_session, symbol="AAPL", llm="gpt-4o-mini")

        assert added_record.asset_id is None


# ---------------------------------------------------------------------------
# live_trading_dal: create_indicator stores asset_id
# ---------------------------------------------------------------------------

class TestCreateIndicatorAssetId:
    @pytest.mark.asyncio
    async def test_stores_asset_id(self):
        from dal.live_trading_dal import create_indicator

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_indicator(
            mock_session, symbol="MSFT", timeframe="1h", asset_id=7, rsi=55.0,
        )

        assert added_record.asset_id == 7
        assert added_record.symbol == "MSFT"

    @pytest.mark.asyncio
    async def test_asset_id_defaults_to_none(self):
        from dal.live_trading_dal import create_indicator

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_indicator(mock_session, symbol="TSLA", timeframe="1d")

        assert added_record.asset_id is None


# ---------------------------------------------------------------------------
# live_trading_dal: create_signal stores asset_id
# ---------------------------------------------------------------------------

class TestCreateSignalAssetId:
    @pytest.mark.asyncio
    async def test_stores_asset_id(self):
        from dal.live_trading_dal import create_signal

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_signal(
            mock_session,
            symbol="AAPL", timeframe="1h",
            action="BUY", confidence=0.7,
            technical_score=0.6, risk_score=0.5, ai_score=0.8,
            asset_id=3,
        )

        assert added_record.asset_id == 3
        assert added_record.symbol == "AAPL"


# ---------------------------------------------------------------------------
# execution_dal: create_order stores asset_id
# ---------------------------------------------------------------------------

class TestCreateOrderAssetId:
    @pytest.mark.asyncio
    async def test_stores_asset_id(self):
        from dal.execution_dal import create_order

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_order(
            mock_session,
            symbol="AAPL", side="buy", qty=10.0,
            asset_id=5,
        )

        assert added_record.asset_id == 5
        assert added_record.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_asset_id_defaults_to_none(self):
        from dal.execution_dal import create_order

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_order(mock_session, symbol="MSFT", side="sell", qty=5.0)

        assert added_record.asset_id is None


# ---------------------------------------------------------------------------
# execution_dal: create_risk_event stores asset_id (nullable)
# ---------------------------------------------------------------------------

class TestCreateRiskEventAssetId:
    @pytest.mark.asyncio
    async def test_stores_asset_id_when_provided(self):
        from dal.execution_dal import create_risk_event

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_risk_event(
            mock_session,
            event_type="stop_loss_triggered",
            description="Stop loss for AAPL",
            symbol="AAPL",
            asset_id=2,
        )

        assert added_record.asset_id == 2

    @pytest.mark.asyncio
    async def test_asset_id_none_for_system_events(self):
        from dal.execution_dal import create_risk_event

        mock_session = AsyncMock()
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_session.add = capture_add
        mock_session.flush = AsyncMock()

        await create_risk_event(
            mock_session,
            event_type="kill_switch_activated",
            description="Kill switch activated",
        )

        assert added_record.asset_id is None
