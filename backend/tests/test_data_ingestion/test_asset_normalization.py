"""Tests for asset uppercase normalization, require_asset_id, and IngestRequest validation."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# upsert_asset: always stores symbol as uppercase
# ---------------------------------------------------------------------------

class TestUpsertAssetNormalization:
    @pytest.mark.asyncio
    async def test_lowercased_symbol_is_uppercased_before_insert(self):
        from dal.market_data_dal import upsert_asset

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        with patch("dal.market_data_dal.get_asset_id_by_symbol", new=AsyncMock(return_value=5)):
            asset_id = await upsert_asset(mock_session, "aapl", asset_type="stock")

        assert asset_id == 5
        call_args = mock_session.execute.call_args
        compiled = str(call_args[0][0].compile(compile_kwargs={"literal_binds": True}))
        assert "AAPL" in compiled
        assert "aapl" not in compiled

    @pytest.mark.asyncio
    async def test_mixed_case_symbol_is_uppercased(self):
        from dal.market_data_dal import upsert_asset

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.flush = AsyncMock()

        with patch("dal.market_data_dal.get_asset_id_by_symbol", new=AsyncMock(return_value=7)):
            result = await upsert_asset(mock_session, "MsFt", asset_type="stock")

        assert result == 7
        compiled = str(mock_session.execute.call_args[0][0].compile(
            compile_kwargs={"literal_binds": True}
        ))
        assert "MSFT" in compiled


# ---------------------------------------------------------------------------
# ensure_asset_for_live_stream: insert-if-missing, never overwrites name
# ---------------------------------------------------------------------------


class TestEnsureAssetForLiveStream:
    @pytest.mark.asyncio
    async def test_inserts_with_on_conflict_do_nothing_and_uppercases_symbol(self):
        from dal.market_data_dal import ensure_asset_for_live_stream

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.flush = AsyncMock()

        with patch("dal.market_data_dal.get_asset_id_by_symbol", new=AsyncMock(return_value=9)):
            asset_id = await ensure_asset_for_live_stream(mock_session, "amzn")

        assert asset_id == 9
        compiled = str(mock_session.execute.call_args[0][0].compile(
            compile_kwargs={"literal_binds": True},
        ))
        upper = compiled.upper()
        assert "ON CONFLICT" in upper
        assert "DO NOTHING" in upper
        assert "DO UPDATE" not in upper
    @pytest.mark.asyncio
    async def test_inserts_crypto_type_for_crypto_pair(self):
        from dal.market_data_dal import ensure_asset_for_live_stream

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.flush = AsyncMock()

        with (
            patch(
                "features.data_ingestion.asset_type_resolver.get_asset_type_by_symbol",
                new=AsyncMock(return_value=None),
            ),
            patch("dal.market_data_dal.get_asset_id_by_symbol", new=AsyncMock(return_value=9)),
        ):
            asset_id = await ensure_asset_for_live_stream(mock_session, "BTC-USD")

        assert asset_id == 9
        compiled = str(mock_session.execute.call_args[0][0].compile(
            compile_kwargs={"literal_binds": True},
        ))
        assert "crypto" in compiled.lower()
        assert "BTC-USD" in compiled


class TestRequireAssetId:
    @pytest.mark.asyncio
    async def test_returns_id_for_registered_symbol(self):
        from dal.market_data_dal import require_asset_id

        mock_session = AsyncMock()
        with patch("dal.market_data_dal.get_asset_id_by_symbol", new=AsyncMock(return_value=3)):
            result = await require_asset_id(mock_session, "AAPL")

        assert result == 3

    @pytest.mark.asyncio
    async def test_raises_value_error_for_unknown_symbol(self):
        from dal.market_data_dal import require_asset_id

        mock_session = AsyncMock()
        with patch("dal.market_data_dal.get_asset_id_by_symbol", new=AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="not registered"):
                await require_asset_id(mock_session, "FAKE")

    @pytest.mark.asyncio
    async def test_uppercases_symbol_for_lookup(self):
        from dal.market_data_dal import require_asset_id

        mock_session = AsyncMock()
        captured = {}

        async def fake_lookup(session, symbol):
            captured["symbol"] = symbol
            return 10

        with patch("dal.market_data_dal.get_asset_id_by_symbol", side_effect=fake_lookup):
            await require_asset_id(mock_session, "tsla")

        assert captured["symbol"] == "tsla"


# ---------------------------------------------------------------------------
# IngestRequest DTO: symbols are normalised to uppercase
# ---------------------------------------------------------------------------

class TestIngestRequestSymbolNormalization:
    def test_lowercase_symbols_are_uppercased(self):
        from dtos.market_data_dto import IngestRequest

        req = IngestRequest(symbols=["aapl", "msft"], timeframes=["1d"])
        assert req.symbols == ["AAPL", "MSFT"]

    def test_mixed_case_symbols_are_uppercased(self):
        from dtos.market_data_dto import IngestRequest

        req = IngestRequest(symbols=["Tsla", "sPY"])
        assert req.symbols == ["TSLA", "SPY"]

    def test_already_uppercase_symbols_unchanged(self):
        from dtos.market_data_dto import IngestRequest

        req = IngestRequest(symbols=["AAPL", "QQQ"])
        assert req.symbols == ["AAPL", "QQQ"]

    def test_symbols_are_stripped(self):
        from dtos.market_data_dto import IngestRequest

        req = IngestRequest(symbols=[" AAPL ", " msft "])
        assert req.symbols == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# AgentAnalysisRequest DTO: symbol is normalised to uppercase
# ---------------------------------------------------------------------------

class TestAgentAnalysisRequestNormalization:
    def test_lowercase_symbol_is_uppercased(self):
        from dtos.ai_agent_dto import AgentAnalysisRequest

        req = AgentAnalysisRequest(symbol="aapl")
        assert req.symbol == "AAPL"

    def test_mixed_case_symbol_is_uppercased(self):
        from dtos.ai_agent_dto import AgentAnalysisRequest

        req = AgentAnalysisRequest(symbol="Tsla")
        assert req.symbol == "TSLA"

    def test_symbol_is_stripped(self):
        from dtos.ai_agent_dto import AgentAnalysisRequest

        req = AgentAnalysisRequest(symbol=" AAPL ")
        assert req.symbol == "AAPL"
