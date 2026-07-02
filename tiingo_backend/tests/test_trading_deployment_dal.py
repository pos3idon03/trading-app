from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from dal import trading_deployment_dal


@pytest.mark.asyncio
async def test_list_deployments_for_ohlcv_refresh_includes_error(monkeypatch):
    dep_active = MagicMock(
        id=uuid4(),
        symbol="AAPL",
        timeframe="1h",
        status="active",
    )
    dep_error = MagicMock(
        id=uuid4(),
        symbol="BTC-USD",
        timeframe="1h",
        status="error",
    )
    inst_stock = MagicMock(asset_type="stock")
    inst_crypto = MagicMock(asset_type="crypto")

    execute_result = MagicMock()
    execute_result.all.return_value = [
        (dep_active, inst_stock),
        (dep_error, inst_crypto),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=execute_result)

    rows = await trading_deployment_dal.list_deployments_for_ohlcv_refresh(session)

    assert len(rows) == 2
    symbols = {row["symbol"] for row in rows}
    assert symbols == {"AAPL", "BTC-USD"}
