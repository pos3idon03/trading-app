from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dal import fundamentals_dal

_T1 = datetime(2023, 9, 30, tzinfo=timezone.utc)
_T2 = datetime(2024, 3, 31, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_annual_falls_back_to_quarterly_aggregation():
    quarterly = [
        {
            "time": _T1,
            "metric_name": "revenue",
            "value": 80.0,
            "period": "2023-Q4",
            "statement_type": "incomeStatement",
        },
        {
            "time": _T2,
            "metric_name": "revenue",
            "value": 90.0,
            "period": "2024-Q1",
            "statement_type": "incomeStatement",
        },
    ]
    session = MagicMock()
    with patch.object(
        fundamentals_dal,
        "_query_fundamentals",
        new=AsyncMock(side_effect=[[], quarterly]),
    ):
        result = await fundamentals_dal.list_fundamentals_for_symbol(
            session, 1, period_type="annual", metric_names=["revenue"], order="asc",
        )

    periods = {r["period"] for r in result}
    assert "FY-2023" in periods
    assert "FY-2024" in periods
