from uuid import uuid4

from features.execution.portfolio_snapshot import (
    alpaca_price_by_tiingo_symbol,
    build_consolidated_position_rows,
    build_untracked_position_rows,
    cap_deployment_quantities,
    compute_attributed_qty_by_symbol,
)


def test_alpaca_price_by_tiingo_symbol_normalizes_btcusd():
    prices = alpaca_price_by_tiingo_symbol(
        [{"symbol": "BTCUSD", "current_price": 73646.36}],
    )
    assert prices == {"BTC-USD": 73646.36}


def test_build_untracked_position_rows_subtracts_attributed_qty():
    alpaca_positions = [
        {
            "symbol": "AAPL",
            "qty": 0.33,
            "side": "long",
            "market_value": 102.55,
            "avg_entry_price": 300,
            "unrealized_pl": 3.30,
            "current_price": 310.76,
        }
    ]
    attributed = {"AAPL": 0.1}
    rows = build_untracked_position_rows(alpaca_positions, attributed)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"
    assert abs(rows[0]["qty"] - 0.23) < 1e-6


def test_build_untracked_position_rows_uses_tiingo_crypto_symbol_keys():
    alpaca_positions = [
        {
            "symbol": "BTCUSD",
            "qty": 0.067,
            "side": "long",
            "market_value": 4935.0,
            "avg_entry_price": 74000,
            "unrealized_pl": -25.0,
            "current_price": 73646.0,
        }
    ]
    rows = build_untracked_position_rows(alpaca_positions, {"BTC-USD": 0.067})
    assert rows == []


def test_build_untracked_position_rows_empty_when_fully_attributed():
    alpaca_positions = [
        {
            "symbol": "AAPL",
            "qty": 1,
            "side": "long",
            "market_value": 100,
            "avg_entry_price": 100,
            "unrealized_pl": 0,
            "current_price": 100,
        }
    ]
    rows = build_untracked_position_rows(alpaca_positions, {"AAPL": 1})
    assert rows == []


def test_compute_attributed_qty_by_symbol_uses_deployment_list():
    deployments = [
        {"symbol": "AAPL", "position_qty": 10},
        {"symbol": "AAPL", "position_qty": 2},
        {"symbol": "MSFT", "position_qty": 0},
    ]
    totals = compute_attributed_qty_by_symbol(deployments)
    assert totals == {"AAPL": 12.0}


def test_cap_deployment_quantities_scales_when_ledger_exceeds_alpaca():
    deployment_id = uuid4()
    deployments = [
        {"id": deployment_id, "symbol": "AAPL", "position_qty": 15.0},
    ]
    capped = cap_deployment_quantities(deployments, {"AAPL": 12.91494})
    assert abs(capped[0]["position_qty"] - 12.91494) < 1e-6
    attributed = compute_attributed_qty_by_symbol(capped)
    rows = build_untracked_position_rows(
        [
            {
                "symbol": "AAPL",
                "qty": 12.91494,
                "side": "long",
                "market_value": 100,
                "avg_entry_price": 100,
                "unrealized_pl": 1,
                "current_price": 100,
            }
        ],
        attributed,
    )
    assert rows == []


def test_untracked_remainder_when_ledger_below_alpaca():
    deployments = [{"id": uuid4(), "symbol": "AAPL", "position_qty": 12.58494}]
    capped = cap_deployment_quantities(deployments, {"AAPL": 12.91494})
    attributed = compute_attributed_qty_by_symbol(capped)
    rows = build_untracked_position_rows(
        [
            {
                "symbol": "AAPL",
                "qty": 12.91494,
                "side": "long",
                "market_value": 100,
                "avg_entry_price": 100,
                "unrealized_pl": 1,
                "current_price": 100,
            }
        ],
        attributed,
    )
    assert len(rows) == 1
    assert abs(rows[0]["qty"] - 0.33) < 0.01


def test_build_consolidated_position_rows_merges_symbol_slices():
    deployment_id = uuid4()
    deployment_rows = [
        {
            "deployment_id": deployment_id,
            "symbol": "AAPL",
            "model_name": "AAPL ml_logistic prices_only",
            "qty": 12.58494,
            "side": "long",
            "market_value": 3918.0,
            "unrealized_pl": 4.4,
            "current_price": 311.0,
            "avg_entry_price": 310.65,
        }
    ]
    untracked_rows = [
        {
            "symbol": "AAPL",
            "qty": 0.33,
            "side": "long",
            "market_value": 102.63,
            "unrealized_pl": 0.2,
            "current_price": 311.0,
            "avg_entry_price": 310.0,
        }
    ]
    period_pl = {
        str(deployment_id): 3918.45,
        "untracked:AAPL:0": 102.75,
    }
    rows = build_consolidated_position_rows(
        deployment_rows,
        untracked_rows,
        period_pl_by_key=period_pl,
    )
    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAPL"
    assert abs(rows[0]["qty"] - 12.91494) < 1e-4
    assert "ml_logistic" in rows[0]["source"]
    assert "Untracked (0.33)" in rows[0]["source"]
    assert abs(rows[0]["period_pl"] - 4021.2) < 0.01
    assert rows[0]["deployment_id"] is None
